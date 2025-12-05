import React from 'react';
import { Routes, Route } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Home from './pages/Home';
import TechTrends from './pages/TechTrends';
import SalaryAnalysis from './pages/SalaryAnalysis';
import PersonalAdvisory from './pages/PersonalAdvisory';

function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/future-landscape" element={<TechTrends />} />
        <Route path="/value-spectrum" element={<SalaryAnalysis />} />
        <Route path="/career-compass" element={<PersonalAdvisory />} />
      </Routes>
    </AppLayout>
  );
}

export default App;
