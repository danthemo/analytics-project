import type { MarketplaceName, ReviewFiltersState } from "../types/domain";


type FiltersProps = {
  filters: ReviewFiltersState;
  marketplaces: MarketplaceName[];
  onChange: (nextFilters: ReviewFiltersState) => void;
};


export function Filters({ filters, marketplaces, onChange }: FiltersProps) {
  return (
    <div className="filters">
      <label className="field">
        <span className="field__label">Площадка</span>
        <select
          className="field__input"
          value={filters.marketplace}
          onChange={(event) => onChange({ ...filters, marketplace: event.target.value })}
        >
          <option value="">Все</option>
          {marketplaces.map((marketplace) => (
            <option key={marketplace} value={marketplace}>
              {marketplace}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span className="field__label">Тональность</span>
        <select
          className="field__input"
          value={filters.sentiment}
          onChange={(event) => onChange({ ...filters, sentiment: event.target.value })}
        >
          <option value="">Все</option>
          <option value="positive">positive</option>
          <option value="neutral">neutral</option>
          <option value="negative">negative</option>
        </select>
      </label>

      <label className="field field--grow">
        <span className="field__label">Поиск по тексту</span>
        <input
          className="field__input"
          type="search"
          value={filters.search}
          onChange={(event) => onChange({ ...filters, search: event.target.value })}
          placeholder="Введите фрагмент отзыва"
        />
      </label>
    </div>
  );
}
