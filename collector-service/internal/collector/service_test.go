package collector

import "testing"

func TestFilterAndDedupeReviews(t *testing.T) {
	input := []Review{
		{Source: "wildberries", ProductURL: "wb", Text: " Отличный  товар "},
		{Source: "wildberries", ProductURL: "wb", Text: "отличный товар"},
		{Source: "wildberries", ProductURL: "wb", Text: "ОТЛИЧНЫЙ   ТОВАР"},
		{Source: "wildberries", ProductURL: "wb", Text: "ёжик хороший"},
		{Source: "wildberries", ProductURL: "wb", Text: "ежик   хороший"},
		{Source: "ozon", ProductURL: "ozon", Text: "отличный товар"},
		{Source: "ozon", ProductURL: "ozon", Text: "12345"},
		{Source: "ozon", ProductURL: "ozon", Text: "..."},
		{Source: "ozon", ProductURL: "ozon", Text: "норм"},
	}

	got := filterAndDedupeReviews(input)
	if len(got) != 3 {
		t.Fatalf("expected 3 reviews after filtering, got %d", len(got))
	}

	if got[0].Text != "Отличный товар" {
		t.Fatalf("unexpected first text: %q", got[0].Text)
	}

	if got[1].Text != "ёжик хороший" {
		t.Fatalf("unexpected second text: %q", got[1].Text)
	}

	if got[2].Source != "ozon" || got[2].Text != "отличный товар" {
		t.Fatalf("unexpected third review: %+v", got[2])
	}
}
