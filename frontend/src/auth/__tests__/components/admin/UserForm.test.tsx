// // src/auth/__tests__/components/admin/UserForm.test.tsx
// import React from 'react';
// import { render, screen, fireEvent, waitFor } from '@testing-library/react';
// import userEvent from '@testing-library/user-event';
// import { UserForm } from '../../../components/admin/UserForm';
// import { USER_ROLES, USER_PERMISSIONS } from '../../../constants';

// describe('UserForm', () => {
//   const mockOnSubmit = jest.fn();
//   const mockOnCancel = jest.fn();
//   const defaultProps = {
//     onSubmit: mockOnSubmit,
//     onCancel: mockOnCancel
//   };

//   beforeEach(() => {
//     jest.clearAllMocks();
//   });

//   it('renders empty form for new user', () => {
//     render(<UserForm {...defaultProps} />);

//     expect(screen.getByLabelText(/first name/i)).toHaveValue('');
//     expect(screen.getByLabelText(/last name/i)).toHaveValue('');
//     expect(screen.getByLabelText(/email/i)).toHaveValue('');
//     expect(screen.getByLabelText(/role/i)).toHaveValue('user');
//   });

//   it('renders form with user data for editing', () => {
//     const user = {
//       firstName: 'John',
//       lastName: 'Doe',
//       email: 'john@example.com',
//       role: 'admin',
//       permissions: [USER_PERMISSIONS.VIEW_USERS]
//     };

//     render(<UserForm {...defaultProps} user={user} />);

//     expect(screen.getByLabelText(/first name/i)).toHaveValue(user.firstName);
//     expect(screen.getByLabelText(/last name/i)).toHaveValue(user.lastName);
//     expect(screen.getByLabelText(/email/i)).toHaveValue(user.email);
//     expect(screen.getByLabelText(/role/i)).toHaveValue(user.role);
//   });

//   it('submits form with valid data', async () => {
//     render(<UserForm {...defaultProps} />);

//     await userEvent.type(screen.getByLabelText(/first name/i), 'John');
//     await userEvent.type(screen.getByLabelText(/last name/i), 'Doe');
//     await userEvent.type(screen.getByLabelText(/email/i), 'john@example.com');
    
//     const roleSelect = screen.getByLabelText(/role/i);
//     await userEvent.selectOptions(roleSelect, USER_ROLES.ADMIN);

//     const viewUsersCheckbox = screen.getByLabelText(/view users/i);
//     await userEvent.click(viewUsersCheckbox);

//     fireEvent.submit(screen.getByRole('button', { name: /create user/i }));

//     await waitFor(() => {
//       expect(mockOnSubmit).toHaveBeenCalledWith({
//         firstName: 'John',
//         lastName: 'Doe',
//         email: 'john@example.com',
//         role: USER_ROLES.ADMIN,
//         permissions: [USER_PERMISSIONS.VIEW_USERS]
//       });
//     });
//   });

//   it('shows error message when submission fails', async () => {
//     const error = 'Failed to create user';
//     mockOnSubmit.mockRejectedValueOnce(new Error(error));

//     render(<UserForm {...defaultProps} />);

//     await userEvent.type(screen.getByLabelText(/first name/i), 'John');
//     await userEvent.type(screen.getByLabelText(/email/i), 'john@example.com');

//     fireEvent.submit(screen.getByRole('button', { name: /create user/i }));

//     await waitFor(() => {
//       expect(screen.getByText(error)).toBeInTheDocument();
//     });
//   });

//   it('calls onCancel when cancel button is clicked', () => {
//     render(<UserForm {...defaultProps} />);
    
//     fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    
//     expect(mockOnCancel).toHaveBeenCalled();
//   });
// });

