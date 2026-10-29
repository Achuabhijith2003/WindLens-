import '@testing-library/jest-dom';

// Polyfill ResizeObserver for JSDOM when testing Recharts ResponsiveContainer
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
