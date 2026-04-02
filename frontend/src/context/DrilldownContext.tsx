import { createContext, useContext, useState, type ReactNode } from 'react';

interface DrilldownFilters {
  hour?: string;
  category?: string;
}

interface DrilldownContextType {
  filters: DrilldownFilters;
  setFilters: (f: DrilldownFilters) => void;
  clearFilters: () => void;
}

const DrilldownContext = createContext<DrilldownContextType>({
  filters: {},
  setFilters: () => {},
  clearFilters: () => {},
});

export function DrilldownProvider({ children }: { children: ReactNode }) {
  const [filters, setFiltersState] = useState<DrilldownFilters>({});

  const setFilters = (f: DrilldownFilters) => setFiltersState((prev) => ({ ...prev, ...f }));
  const clearFilters = () => setFiltersState({});

  return (
    <DrilldownContext.Provider value={{ filters, setFilters, clearFilters }}>
      {children}
    </DrilldownContext.Provider>
  );
}

export function useDrilldown() {
  return useContext(DrilldownContext);
}
