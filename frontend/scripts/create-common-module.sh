#!/bin/bash

# Base directory for common module
COMMON_DIR="src/common"

# Create main directories
mkdir -p "${COMMON_DIR}"/{api/{client,utils},components/{feedback,layout,navigation,ui/{buttons,inputs,data,overlays}},constants,hooks,providers,store/ui,styles/{theme,global},types,utils/{date,string,number,validation}}

# Create API files
touch "${COMMON_DIR}"/api/client/{axiosClient,interceptors,index}.ts
touch "${COMMON_DIR}"/api/utils/{apiUtils,errorHandlers,retryUtils}.ts
touch "${COMMON_DIR}"/api/index.ts

# Create component files
touch "${COMMON_DIR}"/components/feedback/{Alert,Loader,Progress,index}.tsx
touch "${COMMON_DIR}"/components/layout/{MainLayout,Header,Sidebar,Footer,index}.tsx
touch "${COMMON_DIR}"/components/navigation/{Breadcrumbs,NavLink,index}.tsx

# Create UI component files
touch "${COMMON_DIR}"/components/ui/buttons/{Button,IconButton,index}.tsx
touch "${COMMON_DIR}"/components/ui/inputs/{TextField,Select,index}.tsx
touch "${COMMON_DIR}"/components/ui/data/{Table,Pagination,index}.tsx
touch "${COMMON_DIR}"/components/ui/overlays/{Modal,Dialog,index}.tsx
touch "${COMMON_DIR}"/components/ui/index.ts

# Create constants files
touch "${COMMON_DIR}"/constants/{api,routes,regex,index}.ts

# Create hook files
touch "${COMMON_DIR}"/hooks/{useDebounce,usePagination,useQueryParams,useWindowSize,index}.ts

# Create provider files
touch "${COMMON_DIR}"/providers/{ThemeProvider,ToastProvider,index}.tsx

# Create store files
touch "${COMMON_DIR}"/store/ui/{uiSlice,selectors,index}.ts
touch "${COMMON_DIR}"/store/index.ts

# Create style files
touch "${COMMON_DIR}"/styles/theme/{colors,typography,spacing,index}.ts
touch "${COMMON_DIR}"/styles/global/{reset,base}.css
touch "${COMMON_DIR}"/styles/index.ts

# Create type files
touch "${COMMON_DIR}"/types/{api,components,store,index}.ts

# Create util files
touch "${COMMON_DIR}"/utils/date/{formatters,validators,index}.ts
touch "${COMMON_DIR}"/utils/string/{formatters,validators,index}.ts
touch "${COMMON_DIR}"/utils/number/{formatters,calculations,index}.ts
touch "${COMMON_DIR}"/utils/validation/{schemas,rules,index}.ts
touch "${COMMON_DIR}"/utils/index.ts

# Create main index file
touch "${COMMON_DIR}"/index.ts

echo "Common module structure created successfully!"

# Add basic exports to main index.ts
cat > "${COMMON_DIR}"/index.ts << EOL
export * from './components';
export * from './hooks';
export * from './utils';
export * from './types';
export * from './constants';
export { axiosClient } from './api/client';
EOL

# Add basic component index exports
cat > "${COMMON_DIR}"/components/ui/index.ts << EOL
export * from './buttons';
export * from './inputs';
export * from './data';
export * from './overlays';
EOL

echo "Basic exports added to index files!"