import React from 'react';
import { Routes, Route } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Home from './pages/Home';
import TechTrends from './pages/TechTrends';
import SalaryAnalysis from './pages/SalaryAnalysis';
import PersonalAdvice from './pages/PersonalAdvice';

function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/future-landscape" element={<TechTrends />} />
        <Route path="/value-spectrum" element={<SalaryAnalysis />} />
        <Route path="/career-compass" element={<PersonalAdvice />} />
      </Routes>
    </AppLayout>
  );
}

export default App;
