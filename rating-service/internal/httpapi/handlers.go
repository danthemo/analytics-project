package httpapi

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"

	"rating-service/internal/service"
)

type Handler struct {
	service *service.RatingService
}

func New(ratingService *service.RatingService) *Handler {
	return &Handler{service: ratingService}
}

func (h *Handler) Register() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", h.health)
	mux.HandleFunc("POST /api/v1/reviews/{reviewID}/analyze", h.analyzeReview)
	mux.HandleFunc("GET /api/v1/products/{productID}/rating", h.getProductRating)
	mux.HandleFunc("POST /api/v1/products/{productID}/rating/recalculate", h.recalculateProduct)
	mux.HandleFunc("POST /api/v1/ratings/recalculate-all", h.recalculateAll)
	return mux
}

func (h *Handler) health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{
		"status": "ok",
	})
}

func (h *Handler) analyzeReview(w http.ResponseWriter, r *http.Request) {
	reviewID, err := parseReviewID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid review id")
		return
	}

	result, err := h.service.AnalyzeReview(r.Context(), reviewID)
	if errors.Is(err, service.ErrReviewNotFound) {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	if err != nil {
		writeError(w, http.StatusBadGateway, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, result)
}

func (h *Handler) getProductRating(w http.ResponseWriter, r *http.Request) {
	productID, err := parseProductID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid product id")
		return
	}

	result, err := h.service.GetProductResult(r.Context(), productID)
	if errors.Is(err, service.ErrProductNotFound) {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, result)
}

func (h *Handler) recalculateProduct(w http.ResponseWriter, r *http.Request) {
	productID, err := parseProductID(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid product id")
		return
	}

	result, err := h.service.RecalculateProduct(r.Context(), productID)
	if errors.Is(err, service.ErrProductNotFound) {
		writeError(w, http.StatusNotFound, err.Error())
		return
	}
	if errors.Is(err, service.ErrNoAnalyzedReviews) {
		writeError(w, http.StatusConflict, err.Error())
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, result)
}

func (h *Handler) recalculateAll(w http.ResponseWriter, r *http.Request) {
	results, err := h.service.RecalculateAll(r.Context())
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"processed_products": len(results),
		"results":            results,
	})
}

func parseProductID(r *http.Request) (int64, error) {
	rawID := r.PathValue("productID")
	return strconv.ParseInt(rawID, 10, 64)
}

func parseReviewID(r *http.Request) (int64, error) {
	rawID := r.PathValue("reviewID")
	return strconv.ParseInt(rawID, 10, 64)
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, status int, message string) {
	writeJSON(w, status, map[string]string{
		"error": message,
	})
}
