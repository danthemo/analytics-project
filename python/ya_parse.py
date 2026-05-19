import re
from urllib.parse import quote, urlparse, urlunparse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


app = FastAPI()


class ParseRequest(BaseModel):
    query: str
    headless: bool = True
    product_candidates_limit: int = 5


class Review(BaseModel):
    text: str


class ProductInfo(BaseModel):
    url: str
    reviews_url: str


class ParseResponse(BaseModel):
    source: str
    query: str
    product: ProductInfo
    reviews_count: int
    reviews: list[Review]


@app.post("/parse/yandex-market", response_model=ParseResponse)
async def parse_yandex_market(req: ParseRequest):
    return await collect_yandex_market_reviews(
        query=req.query,
        headless=req.headless,
        product_candidates_limit=req.product_candidates_limit,
    )


async def collect_yandex_market_reviews(
    query: str,
    headless: bool = True,
    product_candidates_limit: int = 5,
) -> dict:
    search_url = f"https://market.yandex.ru/search?text={quote(query)}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1440, "height": 1000},
            locale="ru-RU",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/148.0.0.0 Safari/537.36"
            ),
        )

        page = await context.new_page()

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(4000)

            product_url = await get_best_product_url(
                page=page,
                limit=product_candidates_limit,
            )

            if not product_url:
                raise HTTPException(
                    status_code=404,
                    detail="Не удалось найти подходящий товар в выдаче",
                )

            reviews_url = make_reviews_url(product_url)

            await page.goto(reviews_url, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(4000)

            await scroll_until_reviews_loaded(page)

            reviews = await extract_reviews(page)

            return {
                "source": "yandex_market",
                "query": query,
                "product": {
                    "url": product_url,
                    "reviews_url": reviews_url,
                },
                "reviews_count": len(reviews),
                "reviews": reviews,
            }

        except PlaywrightTimeoutError:
            raise HTTPException(
                status_code=504,
                detail="Timeout при загрузке Яндекс Маркета",
            )

        finally:
            await browser.close()


async def get_best_product_url(page, limit: int = 5) -> str | None:
    """
    Берем первые N карточек из выдачи и выбираем товар
    с максимальным количеством отзывов/оценок.
    """

    products = await page.evaluate(
        """
        (limit) => {
            const links = Array.from(document.querySelectorAll('a[href*="/card/"]'));

            const unique = [];
            const seen = new Set();

            function normalizeText(text) {
                return (text || '').replace(/\\s+/g, ' ').trim();
            }

            function findCardElement(a) {
                let current = a;

                for (let i = 0; i < 8; i++) {
                    if (!current) break;

                    const text = normalizeText(current.innerText);

                    if (
                        text.length > 50 &&
                        (
                            text.includes('₽') ||
                            text.includes('отзыв') ||
                            text.includes('оцен') ||
                            text.includes('рейтинг')
                        )
                    ) {
                        return current;
                    }

                    current = current.parentElement;
                }

                return a;
            }

            for (const a of links) {
                const href = a.href;

                if (!href) continue;
                if (!href.includes('/card/')) continue;
                if (href.includes('/reviews')) continue;

                const cleanUrl = href.split('#')[0];

                if (seen.has(cleanUrl)) continue;

                const card = findCardElement(a);
                const text = card ? normalizeText(card.innerText) : normalizeText(a.innerText);

                seen.add(cleanUrl);

                unique.push({
                    url: cleanUrl,
                    text: text
                });

                if (unique.length >= limit) {
                    break;
                }
            }

            return unique;
        }
        """,
        limit,
    )

    if not products:
        return None

    best_url = None
    best_reviews_count = -1

    for product in products:
        url = product.get("url")
        text = product.get("text", "")

        reviews_count = extract_reviews_count_from_text(text)

        print(f"candidate: reviews={reviews_count}, url={url}")

        if reviews_count > best_reviews_count:
            best_reviews_count = reviews_count
            best_url = url

    return best_url


def extract_reviews_count_from_text(text: str) -> int:
    """
    Достает количество отзывов/оценок из текста карточки.

    Примеры:
    123 отзыва
    1 234 отзывов
    12 оценок
    2 531 оценка
    """

    if not text:
        return 0

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    patterns = [
        r"(\d[\d\s]*)\s+отзыв(?:ов|а)?",
        r"(\d[\d\s]*)\s+оцен(?:ок|ки|ка)",
    ]

    counts = []

    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)

        for match in matches:
            number = re.sub(r"\s+", "", match)

            try:
                counts.append(int(number))
            except ValueError:
                pass

    if not counts:
        return 0

    return max(counts)


def make_reviews_url(product_url: str) -> str:
    """
    Из:
    https://market.yandex.ru/card/name/123456?...
    делаем:
    https://market.yandex.ru/card/name/123456/reviews
    """

    parsed = urlparse(product_url)
    path = parsed.path.rstrip("/")

    if not path.endswith("/reviews"):
        path += "/reviews"

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            path,
            "",
            "",
            "",
        )
    )


async def scroll_until_reviews_loaded(page):
    """
    Скроллим страницу отзывов, пока отзывы перестают подгружаться.
    """

    previous_height = 0
    same_height_count = 0

    for _ in range(100):
        current_height = await page.evaluate("document.body.scrollHeight")

        await page.mouse.wheel(0, 2500)
        await page.wait_for_timeout(1200)

        if current_height == previous_height:
            same_height_count += 1
        else:
            same_height_count = 0

        if same_height_count >= 6:
            break

        previous_height = current_height


async def extract_reviews(page) -> list[dict]:
    """
    Возвращает массив отдельных текстов:

    [
      {"text": "отличная помада"},
      {"text": "хорошо увлажняет губы"}
    ]

    Берем только содержимое после:
    Достоинства / Недостатки / Комментарий
    """

    values = await page.evaluate(
        """
        () => {
            const result = [];
            const nodes = Array.from(document.querySelectorAll('div, span, p'));

            const labels = [
                'Достоинства',
                'Недостатки',
                'Комментарий',
                'Достоинства:',
                'Недостатки:',
                'Комментарий:'
            ];

            function normalizeText(text) {
                return (text || '').replace(/\\s+/g, ' ').trim();
            }

            function isLabel(text) {
                const normalized = normalizeText(text);
                return labels.includes(normalized);
            }

            function startsWithLabel(text) {
                const normalized = normalizeText(text);
                return (
                    normalized.startsWith('Достоинства:') ||
                    normalized.startsWith('Недостатки:') ||
                    normalized.startsWith('Комментарий:')
                );
            }

            for (const el of nodes) {
                const text = normalizeText(el.innerText);

                if (!text) continue;
                if (text.length < 3) continue;
                if (text.length > 1500) continue;

                // Вариант 1:
                // элемент уже содержит "Комментарий: отличный товар"
                if (startsWithLabel(text)) {
                    result.push(text);
                    continue;
                }

                // Вариант 2:
                // элемент — это только заголовок "Комментарий",
                // а значение лежит рядом в соседнем элементе
                if (isLabel(text)) {
                    const parent = el.parentElement;
                    if (!parent) continue;

                    const siblings = Array.from(parent.children);
                    const index = siblings.indexOf(el);

                    for (let i = index + 1; i < siblings.length; i++) {
                        const siblingText = normalizeText(siblings[i].innerText);

                        if (!siblingText) continue;

                        if (isLabel(siblingText) || startsWithLabel(siblingText)) {
                            break;
                        }

                        result.push(siblingText);
                        break;
                    }
                }
            }

            return result;
        }
        """
    )

    result = []
    seen = set()

    for value in values:
        cleaned = clean_review_value(value)

        if not cleaned:
            continue

        if len(cleaned) < 5:
            continue

        if looks_like_trash(cleaned):
            continue

        key = normalize_for_dedupe(cleaned)

        if key in seen:
            continue

        seen.add(key)
        result.append({"text": cleaned})

    return result


def clean_review_value(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"\r", " ", value)
    value = re.sub(r"\n+", " ", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    value = value.strip()

    # Убираем названия полей.
    value = re.sub(
        r"^(Достоинства|Недостатки|Комментарий):?\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )

    # Иногда несколько полей склеиваются в одну строку.
    value = re.sub(
        r"\s+(Достоинства|Недостатки|Комментарий):\s*",
        " ",
        value,
        flags=re.IGNORECASE,
    )

    trash_phrases = [
        "Читать полностью",
        "Скрыть",
        "Пожаловаться",
        "Ответить",
        "Полезный отзыв",
        "Комментировать",
        "В избранное",
        "Добавить в избранное",
    ]

    for phrase in trash_phrases:
        value = value.replace(phrase, "")

    trash_patterns = [
        r"\bКоличество упаковок в товаре:.*",
        r"\bОпыт использования:.*",
        r"\bЦвет товара:.*",
        r"\bВкус:.*",
        r"\bАромат:.*",
        r"\bТовар куплен на Маркете\b",
        r"\bКуплен на Маркете\b",
    ]

    for pattern in trash_patterns:
        value = re.sub(pattern, "", value, flags=re.IGNORECASE)

    # Убираем одиночные числа типа 0, 1, 2, которые часто попадают из лайков.
    value = re.sub(r"(^|\s)\d+($|\s)", " ", value)

    value = re.sub(r"\s{2,}", " ", value)
    value = value.strip(" .,\n\t")

    return value


def looks_like_trash(text: str) -> bool:
    normalized = normalize_for_dedupe(text)

    trash_exact = {
        "0",
        "1",
        "2",
        "3",
        "4",
        "5",
        "читать полностью",
        "скрыть",
        "пожаловаться",
        "ответить",
        "полезный отзыв",
        "комментировать",
        "достоинства",
        "недостатки",
        "комментарий",
    }

    if normalized in trash_exact:
        return True

    trash_prefixes = (
        "количество упаковок",
        "опыт использования",
        "цвет товара",
        "вкус",
        "аромат",
        "товар куплен",
        "куплен на маркете",
        "сортировка",
        "сначала новые",
        "сначала старые",
        "сначала полезные",
        "показать еще",
    )

    if normalized.startswith(trash_prefixes):
        return True

    # Если текст почти весь из цифр/символов — это мусор.
    letters = re.findall(r"[a-zA-Zа-яА-ЯёЁ]", text)
    if len(letters) < 3:
        return True

    return False


def normalize_for_dedupe(text: str) -> str:
    text = text.lower()
    text = text.replace("ё", "е")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "ya_parse:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )