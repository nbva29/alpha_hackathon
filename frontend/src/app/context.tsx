import * as React from 'react';
import { createContext, useContext } from 'react';
import { getWorkspace, getApplication, type Need } from '../mock-api';

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
  userId: string;
  route: ReturnType<typeof readRoute>;
  need: Need;
  setNeed: (value: Need) => void;
  selected: string[];
  setSelected: React.Dispatch<React.SetStateAction<string[]>>;
  go: (page: string, id?: string) => void;
  run: (action: () => void) => void;
  notice: (message: string, error?: boolean) => void;
  refresh: () => void;
}
export const AppContext = createContext<AppContextValue | null>(null);
export function useApp() {
  const value = useContext(AppContext);
  if (!value) throw new Error('Нет контекста приложения');
  return value;
}
export function useWorkspace() {
  return getWorkspace(useApp().userId);
}
export function useApplication() {
  const { userId, route } = useApp();
  return getApplication(userId, route.id);
}
export function values(form: HTMLFormElement) {
  return Object.fromEntries(new FormData(form).entries());
}
