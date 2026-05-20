import { useState } from "react";
import type { FormEvent } from "react";


type AddProductFormProps = {
  onSubmit: (name: string) => Promise<void>;
};


export function AddProductForm({ onSubmit }: AddProductFormProps) {
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Введите название товара");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await onSubmit(trimmedName);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Не удалось запустить анализ");
      setLoading(false);
      return;
    }

    setLoading(false);
  };

  return (
    <form className="card form-card" onSubmit={handleSubmit}>
      <h2 className="section-title">Добавить товар</h2>
      <p className="section-subtitle">
        Frontend отправляет только название товара в API Gateway. Дальнейший сбор, анализ и расчет
        рейтинга происходят на backend.
      </p>

      <label className="field">
        <span className="field__label">Название товара</span>
        <input
          className="field__input"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Игровой руль Logitech G29"
          disabled={loading}
        />
      </label>

      {loading ? <div className="alert alert--info">Идет сбор и анализ отзывов</div> : null}
      {error ? <div className="alert alert--error">{error}</div> : null}

      <div className="form-actions">
        <button type="submit" className="button button--primary" disabled={loading}>
          {loading ? "Обработка..." : "Запустить анализ"}
        </button>
      </div>
    </form>
  );
}
