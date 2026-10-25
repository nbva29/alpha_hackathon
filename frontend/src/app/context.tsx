import * as React from 'react';
import { createContext, useContext } from 'react';
import type { Application, Company, Need, Product } from '../mock-api';
import type { User } from '../api';

export const defaultNeed: Need = {
  purpose: 'Закупка оборудования',
  category: 'development',
  amount: 1200000,
  term: 24,
};
export const readRoute = () => {
  const [path, query] = (location.hash.slice(1) || '/home').split('?');
  return {
    page: path.replace(/^\//, '') || 'home',
    id: new URLSearchParams(query || '').get('id') || '',
  };
};

export interface AppContextValue {
  user: User;
  company: Company | null;
  applications: Application[];
  products: Product[];
  route: ReturnType<typeof readRoute>;
  need: Need;
  setNeed: (value: Need) => void;
  selected: string[];
  setSelected: React.Dispatch<React.SetStateAction<string[]>>;
  go: (page: string, id?: string) => void;
  run: (action: () => Promise<unknown> | void) => Promise<void>;
  notice: (message: string, error?: boolean) => void;
  refresh: () => Promise<void>;
}
export const AppContext = createContext<AppContextValue | null>(null);
export function useApp() {
  const value = useContext(AppContext);
  if (!value) throw new Error('Нет контекста приложения');
  return value;
}
export function useWorkspace() {
  const { company, applications } = useApp();
  return { company, applications };
}
export function useApplication() {
  const { applications, route } = useApp();
  const application = applications.find((item) => item.id === route.id);
  if (!application) throw new Error('Заявка не найдена');
  return application;
}
export function values(form: HTMLFormElement) {
  return Object.fromEntries(new FormData(form).entries());
}
