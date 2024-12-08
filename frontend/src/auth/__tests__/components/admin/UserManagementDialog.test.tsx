// // src/auth/__tests__/components/admin/UserManagementDialog.test.tsx
// import React from 'react';
// import { render, screen, fireEvent } from '@testing-library/react';
// import { UserManagementDialog } from '../../../components/admin/UserManagementDialog';

// describe('UserManagementDialog', () => {
//   const mockOnClose = jest.fn();
//   const mockOnSubmit = jest.fn();
//   const defaultProps = {
//     open: true,
//     onClose: mockOnClose,
//     onSubmit: mockOnSubmit
//   };

//   beforeEach(() => {
//     jest.clearAllMocks();
//   });

//   it('renders create dialog when no user is provided', () => {
//     render(<UserManagementDialog {...defaultProps} />);
    
//     expect(screen.getByText(/create new user/i)).toBeInTheDocument();
//   });

//   it('renders edit dialog when user is provided', () => {
//     const user = {
//       firstName: 'John',
//       lastName: 'Doe',
//       email: 'john@example.com'
//     };

//     render(<UserManagementDialog {...defaultProps} user={user} />);
    
//     expect(screen.getByText(/edit user/i)).toBeInTheDocument();
//     expect(screen.getByDisplayValue(user.firstName)).toBeInTheDocument();
//     expect(screen.getByDisplayValue(user.email)).toBeInTheDocument();
//   });

//   it('calls onClose when dialog is closed', () => {
//     render(<UserManagementDialog {...defaultProps} />);
    
//     fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    
//     expect(mockOnClose).toHaveBeenCalled();
//   });
// });