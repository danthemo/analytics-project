const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const API_PREFIX = import.meta.env.VITE_API_PREFIX ?? "/api";
export const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API !== "false";


function buildUrl(path: string) {
  return `${API_BASE_URL}${API_PREFIX}${path}`;
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildUrl(path), {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const fallbackMessage = "Не удалось выполнить запрос";
    try {
      const data = (await response.json()) as { detail?: string; message?: string };
      throw new Error(data.detail ?? data.message ?? fallbackMessage);
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(fallbackMessage);
    }
  }

  return (await response.json()) as T;
}
