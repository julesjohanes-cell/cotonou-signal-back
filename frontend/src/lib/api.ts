const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export interface HealthResponse {
  status: string;
  service: string;
  timestamp: string;
  version: string;
}

export interface FeatureItem {
  id: number;
  title: string;
  status: string;
}

export interface FeaturesResponse {
  project: string;
  architecture: string;
  items: FeatureItem[];
}

export async function checkBackendHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health/`, {
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error(`Erreur HTTP: ${response.status}`);
  }
  return response.json();
}

export async function fetchFeatures(): Promise<FeaturesResponse> {
  const response = await fetch(`${API_BASE_URL}/features/`, {
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error(`Erreur HTTP: ${response.status}`);
  }
  return response.json();
}
