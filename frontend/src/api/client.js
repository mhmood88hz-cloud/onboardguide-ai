import axios from 'axios';

const client = axios.create({
  baseURL: 'http://localhost:8000', // Passe deine Backend-URL an
});

// Token automatisch bei jedem Request anhängen
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token'); // Oder wie dein Token-Key im Storage heißt
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export default client;