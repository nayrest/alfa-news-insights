import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { HomePage } from './pages/HomePage';
import { InsightsPage } from './pages/InsightsPage';
import { CompanyProvider } from './state/CompanyContext';
import './styles.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CompanyProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="insights/:id?" element={<InsightsPage />} />
            {/* Остальные пункты меню — заглушки, ведут на главную */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </CompanyProvider>
  </StrictMode>,
);
