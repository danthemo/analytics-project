import type { Review } from "../types/domain";
import { formatShortDate } from "../utils/format";


type ReviewsTableProps = {
  reviews: Review[];
};


export function ReviewsTable({ reviews }: ReviewsTableProps) {
  if (reviews.length === 0) {
    return <div className="empty-box">По выбранным фильтрам отзывы не найдены.</div>;
  }

  return (
    <div className="table-wrapper">
      <table className="reviews-table">
        <thead>
          <tr>
            <th>Площадка</th>
            <th>Текст отзыва</th>
            <th>Тональность</th>
            <th>Confidence</th>
            <th>Дата</th>
          </tr>
        </thead>
        <tbody>
          {reviews.map((review) => (
            <tr key={review.id}>
              <td>{review.marketplace}</td>
              <td className="reviews-table__text">{review.text}</td>
              <td>
                <span className={`sentiment-pill sentiment-pill--${review.sentiment}`}>
                  {review.sentiment}
                </span>
              </td>
              <td>{review.confidence ? review.confidence.toFixed(2) : "—"}</td>
              <td>{review.createdAt ? formatShortDate(review.createdAt) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
