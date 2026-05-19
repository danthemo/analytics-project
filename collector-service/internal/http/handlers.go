package httptransport

import (
	"encoding/json"
	"errors"
	"net/http"

	"collector-service/internal/collector"
)

type Handler struct {
	service *collector.Service
}

func New(service *collector.Service) *Handler {
	return &Handler{service: service}
}

func (h *Handler) Register() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", h.health)
	mux.HandleFunc("POST /collect/reviews", h.collectReviews)
	return mux
}

func (h *Handler) health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{
		"status": "ok",
	})
}

func (h *Handler) collectReviews(w http.ResponseWriter, r *http.Request) {
	var req collector.CollectRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid json body")
		return
	}

	response, err := h.service.Collect(r.Context(), req.Query, req.Sources)
	if errors.Is(err, collector.ErrEmptyQuery) {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, response)
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
