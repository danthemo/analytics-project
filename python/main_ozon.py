import re
from urllib.parse import quote, urlparse, urlunparse, parse_qs, urlencode

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


app = FastAPI()


class ParseRequest(BaseModel):
    query: str
    search_url: str | None = None
    product_url: str | None = None
    headless: bool = True


class Review(BaseModel):
    text: str


class ProductInfo(BaseModel):
    url: str
    reviews_url: str | None = None


class ParseResponse(BaseModel):
    source: str
    query: str
    product: ProductInfo
    reviews_count: int
    reviews: list[Review]


@app.post("/parse/ozon", response_model=ParseResponse)
async def parse_ozon(req: ParseRequest):
    return await collect_ozon_reviews(
        query=req.query,
        search_url=req.search_url,
        product_url=req.product_url,
        headless=req.headless,
    )


async def collect_ozon_reviews(
    query: str,
    search_url: str | None = None,
    product_url: str | None = None,
    headless: bool = True,
) -> dict:
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
            if product_url:
                final_product_url = product_url
            else:
                if search_url:
                    target_search_url = replace_query_text(search_url, query)
                else:
                    target_search_url = make_ozon_search_url(query)

                print("search_url:", target_search_url)

                await page.goto(target_search_url, wait_until="domcontentloaded", timeout=60_000)
                await page.wait_for_timeout(6000)

                final_product_url = await get_first_ozon_product_url(page)

                if not final_product_url:
                    await save_debug_files(page)
                    raise HTTPException(
                        status_code=404,
                        detail="Не удалось найти первую карточку товара Ozon",
                    )

            print("product_url:", final_product_url)

            await page.goto(final_product_url, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(7000)

            reviews_url = await open_reviews_like_user(page, final_product_url)

            await scroll_to_reviews_section(page)
            await scroll_reviews(page)

            reviews = await extract_ozon_reviews(page)

            if len(reviews) == 0:
                await save_debug_files(page)

            return {
                "source": "ozon",
                "query": query,
                "product": {
                    "url": final_product_url,
                    "reviews_url": reviews_url,
                },
                "reviews_count": len(reviews),
                "reviews": reviews,
            }

        except PlaywrightTimeoutError:
            raise HTTPException(
                status_code=504,
                detail="Timeout при загрузке Ozon",
            )

        finally:
            await browser.close()


def make_ozon_search_url(query: str) -> str:
    params = {
        "text": query,
        "from_global": "true",
    }
    return "https://www.ozon.ru/search/?" + urlencode(params)


def replace_query_text(url: str, query: str) -> str:
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    query_params["text"] = [query]

    new_query = urlencode(query_params, doseq=True)

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            "",
            new_query,
            "",
        )
    )


async def get_first_ozon_product_url(page) -> str | None:
    links = await page.locator('a[href*="/product/"]').evaluate_all(
        """
        els => els
            .map(a => a.href)
            .filter(Boolean)
        """
    )

    cleaned = []

    for link in links:
        if "/product/" not in link:
            continue

        if "/reviews" in link:
            continue

        if "/questions" in link:
            continue

        clean_url = link.split("#")[0]

        if clean_url in cleaned:
            continue

        cleaned.append(clean_url)

    return cleaned[0] if cleaned else None


async def open_reviews_like_user(page, product_url: str) -> str:
    print("opening product page:", page.url)

    clicked_tab = await click_reviews_tab_js(page)
    print("clicked reviews tab:", clicked_tab)

    if await wait_for_reviews_or_timeout(page, 15_000):
        return page.url

    clicked_counter = await click_reviews_counter_js(page)
    print("clicked reviews counter:", clicked_counter)

    if await wait_for_reviews_or_timeout(page, 15_000):
        return page.url

    reviews_url = make_ozon_reviews_url(product_url)
    print("trying direct reviews url:", reviews_url)

    await page.goto(reviews_url, wait_until="domcontentloaded", timeout=60_000)
    await page.wait_for_timeout(7000)

    if await wait_for_reviews_or_timeout(page, 15_000):
        return reviews_url

    await save_debug_files(page)

    return page.url


async def wait_for_reviews_or_timeout(page, timeout_ms: int = 15_000) -> bool:
    elapsed = 0
    step = 1000

    while elapsed < timeout_ms:
        if await has_reviews_loaded(page):
            return True

        await page.wait_for_timeout(step)
        elapsed += step

    return False


async def click_reviews_tab_js(page) -> bool:
    return await page.evaluate(
        """
        () => {
            function norm(text) {
                return (text || '').replace(/\\s+/g, ' ').trim();
            }

            const elements = Array.from(document.querySelectorAll('a, button, div, span'));

            for (const el of elements) {
                const text = norm(el.innerText);

                if (!text) continue;

                const isReviewsTab =
                    text === 'Отзывы' ||
                    /^Отзывы\\s*\\d*/i.test(text) ||
                    /^Отзывы о товаре/i.test(text);

                if (!isReviewsTab) continue;

                const clickable = el.closest('a, button') || el;

                clickable.scrollIntoView({
                    behavior: 'instant',
                    block: 'center',
                    inline: 'center'
                });

                clickable.click();

                return true;
            }

            return false;
        }
        """
    )


async def click_reviews_counter_js(page) -> bool:
    return await page.evaluate(
        """
        () => {
            function norm(text) {
                return (text || '').replace(/\\s+/g, ' ').trim();
            }

            const pattern = /\\d+(?:[.,]\\d+)?\\s*•\\s*[\\d\\s]+\\s+отзыв/i;
            const elements = Array.from(document.querySelectorAll('a, button, div, span'));

            for (const el of elements) {
                const text = norm(el.innerText);

                if (!pattern.test(text)) continue;

                const clickable = el.closest('a, button') || el;

                clickable.scrollIntoView({
                    behavior: 'instant',
                    block: 'center',
                    inline: 'center'
                });

                clickable.click();

                return true;
            }

            return false;
        }
        """
    )


def make_ozon_reviews_url(product_url: str) -> str:
    parsed = urlparse(product_url)

    query_params = parse_qs(parsed.query)
    query_params["tab"] = ["reviews"]
    query_params["reviewsVariantMode"] = ["2"]
    query_params["oos_search"] = ["false"]

    new_query = urlencode(query_params, doseq=True)

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            "",
            new_query,
            "",
        )
    )


async def scroll_to_reviews_section(page):
    for i in range(60):
        if await has_reviews_loaded(page):
            return

        print(f"scroll_to_reviews_section step={i}")
        await page.mouse.wheel(0, 700)
        await page.wait_for_timeout(900)

    print("reviews section was not detected after slow scroll")


async def has_reviews_loaded(page) -> bool:
    review_count = await page.locator("[data-review-uuid]").count()

    if review_count > 0:
        print("reviews detected by data-review-uuid:", review_count)
        return True

    widget_count = await page.locator('[data-widget="webListReviews"]').count()

    if widget_count > 0:
        print("reviews widget detected:", widget_count)
        return True

    body_text = await page.locator("body").inner_text()

    markers = [
        "Показать сначала:",
        "Вам помог этот отзыв?",
        "Отзывы о товаре",
        "Отзывы покупателей",
        "новые и полезные",
        "с высокой оценкой",
    ]

    if any(marker in body_text for marker in markers):
        print("reviews detected by text markers")
        return True

    return False


async def scroll_reviews(page):
    previous_count = -1
    same_count_rounds = 0

    for i in range(120):
        current_count = await page.locator("[data-review-uuid]").count()
        print(f"scroll_reviews step={i}, reviews_count_in_dom={current_count}")

        await page.mouse.wheel(0, 650)
        await page.wait_for_timeout(1000)

        new_count = await page.locator("[data-review-uuid]").count()

        if new_count == previous_count:
            same_count_rounds += 1
        else:
            same_count_rounds = 0

        previous_count = new_count

        if new_count > 0 and same_count_rounds >= 10:
            break


async def extract_ozon_reviews(page) -> list[dict]:
    raw_reviews = await page.evaluate(
        """
        () => {
            const result = [];
            const reviewNodes = Array.from(document.querySelectorAll('[data-review-uuid]'));

            function normalizeText(text) {
                return (text || '').replace(/\\s+/g, ' ').trim();
            }

            for (const review of reviewNodes) {
                const uuid = review.getAttribute('data-review-uuid') || '';

                const candidates = Array.from(review.querySelectorAll('span, div'))
                    .map(el => normalizeText(el.innerText))
                    .filter(Boolean)
                    .filter(text => text.length >= 15)
                    .filter(text => text.length <= 2500);

                result.push({
                    uuid,
                    candidates
                });
            }

            return result;
        }
        """
    )

    result = []
    seen = set()

    for review in raw_reviews:
        candidates = review.get("candidates", [])
        best_text = pick_best_review_text(candidates)

        if not best_text:
            continue

        cleaned = clean_review_text(best_text)

        if not cleaned:
            continue

        if len(cleaned) < 10:
            continue

        if looks_like_trash(cleaned):
            continue

        if is_probably_author_or_date(cleaned):
            continue

        key = normalize_for_dedupe(cleaned)

        if key in seen:
            continue

        seen.add(key)
        result.append({"text": cleaned})

    return result


def pick_best_review_text(candidates: list[str]) -> str:
    cleaned_candidates = []

    for text in candidates:
        text = clean_review_text(text)

        if not text:
            continue

        if looks_like_trash(text):
            continue

        if is_probably_author_or_date(text):
            continue

        if is_probably_hidden_user(text):
            continue

        if is_probably_product_params(text):
            continue

        if is_probably_ui_text(text):
            continue

        cleaned_candidates.append(text)

    if not cleaned_candidates:
        return ""

    cleaned_candidates.sort(key=len, reverse=True)
    return cleaned_candidates[0]


def clean_review_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\r", " ", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()

    trash_phrases = [
        "Читать полностью",
        "Скрыть",
        "Пожаловаться",
        "Ответить",
        "Отзыв полезен",
        "Вам помог этот отзыв?",
        "Добавить в избранное",
        "В избранное",
    ]

    for phrase in trash_phrases:
        text = text.replace(phrase, " ")

    text = re.sub(r"\bДа\s+\d+\b", " ", text)
    text = re.sub(r"\bНет\s+\d+\b", " ", text)
    text = re.sub(r"\b\d+\s+комментар(?:ий|ия|иев)\b", " ", text, flags=re.IGNORECASE)

    text = re.sub(r"\s{2,}", " ", text)
    text = text.strip(" .,\n\t")

    return text


def is_probably_author_or_date(text: str) -> bool:
    normalized = normalize_for_dedupe(text)

    months = (
        "января|февраля|марта|апреля|мая|июня|июля|августа|"
        "сентября|октября|ноября|декабря"
    )

    if re.fullmatch(
        rf"\d{{1,2}}\s+({months})\s+\d{{4}}",
        normalized,
    ):
        return True

    if re.fullmatch(
        rf"[а-яa-zё.\-\s]{{2,60}}\s+\d{{1,2}}\s+({months})\s+\d{{4}}",
        normalized,
        flags=re.IGNORECASE,
    ):
        return True

    if re.fullmatch(
        rf"[а-яa-zё]\s+[а-яa-zё.\-\s]{{2,60}}\s+\d{{1,2}}\s+({months})\s+\d{{4}}",
        normalized,
        flags=re.IGNORECASE,
    ):
        return True

    words = normalized.split()

    if 1 <= len(words) <= 3 and len(normalized) <= 40:
        useful_words = {
            "отлично",
            "хорошо",
            "супер",
            "нормально",
            "работает",
            "понравилось",
            "рекомендую",
            "оригинал",
            "быстро",
            "качественный",
            "классный",
            "доволен",
            "довольна",
            "удобно",
            "плохо",
            "ужасно",
            "сломался",
            "нравится",
        }

        if not any(word in normalized for word in useful_words):
            return True

    return False


def is_probably_hidden_user(text: str) -> bool:
    normalized = normalize_for_dedupe(text)

    hidden_user_values = {
        "пользователь предпочел скрыть свои данные",
        "пользователь предпочёл скрыть свои данные",
    }

    if normalized in hidden_user_values:
        return True

    if re.fullmatch(
        r"[а-яa-zё]\s+пользователь предпоч[её]л скрыть свои данные",
        normalized,
        flags=re.IGNORECASE,
    ):
        return True

    return False


def is_probably_product_params(text: str) -> bool:
    normalized = normalize_for_dedupe(text)

    prefixes = (
        "название цвета",
        "цвет товара",
        "встроенная память",
        "оперативная память",
        "память",
        "версия",
        "комплектация",
        "качество снимков",
        "качество изображения",
        "скорость работы",
        "размер",
        "количество",
    )

    if normalized.startswith(prefixes):
        return True

    if re.search(
        r"(качество снимков|качество изображения|скорость работы|цвет товара|встроенная память|название цвета|размер|количество):",
        normalized,
    ):
        return True

    return False


def is_probably_ui_text(text: str) -> bool:
    normalized = normalize_for_dedupe(text)

    exact = {
        "показать сначала",
        "новые и полезные",
        "с высокой оценкой",
        "вам помог этот отзыв",
        "ответить",
        "читать полностью",
        "скрыть",
        "пожаловаться",
        "пользователь предпочел скрыть свои данные",
        "пользователь предпочёл скрыть свои данные",
    }

    if normalized in exact:
        return True

    prefixes = (
        "показать сначала",
        "вам помог этот отзыв",
        "да ",
        "нет ",
    )

    if normalized.startswith(prefixes):
        return True

    if re.fullmatch(
        r"[а-яa-zё]\s+пользователь предпоч[её]л скрыть свои данные",
        normalized,
        flags=re.IGNORECASE,
    ):
        return True

    return False


def looks_like_trash(text: str) -> bool:
    normalized = normalize_for_dedupe(text)

    if is_probably_hidden_user(text):
        return True

    months = (
        "января|февраля|марта|апреля|мая|июня|июля|августа|"
        "сентября|октября|ноября|декабря"
    )

    if re.fullmatch(
        rf".{{2,70}}\s+\d{{1,2}}\s+({months})\s+\d{{4}}",
        normalized,
        flags=re.IGNORECASE,
    ):
        return True

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
        "отзыв полезен",
        "комментировать",
    }

    if normalized in trash_exact:
        return True

    letters = re.findall(r"[a-zA-Zа-яА-ЯёЁ]", text)

    if len(letters) < 3:
        return True

    return False


def normalize_for_dedupe(text: str) -> str:
    text = text.lower()
    text = text.replace("ё", "е")
    re_space = re.compile(r"\s+")
    text = re_space.sub(" ", text)
    return text.strip()


async def save_debug_files(page):
    try:
        body_text = await page.locator("body").inner_text()
        with open("ozon_debug_body.txt", "w", encoding="utf-8") as f:
            f.write(body_text)

        html = await page.content()
        with open("ozon_debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)

        print("saved ozon_debug_body.txt and ozon_debug_page.html")
    except Exception as e:
        print("failed to save debug files:", e)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main_ozon:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
    )