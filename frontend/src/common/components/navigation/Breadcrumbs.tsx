// src/components/layout/Breadcrumbs.tsx
import { useLocation } from 'react-router-dom';

export const Breadcrumbs: React.FC = () => {
  const location = useLocation();
  const paths = location.pathname.split('/').filter(Boolean);

  return (
    <nav className="px-4 py-2">
      <ol className="flex space-x-2 text-sm">
        {paths.map((path, index) => (
          <li key={path} className="flex items-center">
            {index > 0 && <span className="mx-2">/</span>}
            <span className="capitalize">
              {path}
            </span>
          </li>
        ))}
      </ol>
    </nav>
  );
};
