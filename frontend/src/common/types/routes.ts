// src/common/types/routes.ts
import { ComponentType, LazyExoticComponent } from 'react';
import { RouteObject } from 'react-router-dom';

export interface RouteConfig extends Omit<RouteObject, 'element' | 'children'> {
  path: string;
  element: ComponentType<any> | LazyExoticComponent<ComponentType<any>>;
  role?: 'user' | 'admin';
  children?: RouteConfig[];
}