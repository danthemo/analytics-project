import { formatRating } from "../utils/format";


type RatingBadgeProps = {
  rating: number;
};


export function RatingBadge({ rating }: RatingBadgeProps) {
  return <span className="rating-badge">{formatRating(rating)}</span>;
}
