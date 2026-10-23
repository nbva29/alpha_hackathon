import { createRoot } from 'react-dom/client';
import { App } from './App';
import './styles.css';

const container = document.getElementById('app');
if (!container) throw new Error('Корневой элемент приложения не найден');
createRoot(container).render(<App />);
