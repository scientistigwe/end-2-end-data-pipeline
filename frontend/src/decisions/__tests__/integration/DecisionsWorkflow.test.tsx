// // src/decisions/__tests__/integration/DecisionWorkflow.test.tsx
// import React from 'react';
// import { render, screen, fireEvent, waitFor } from '@testing-library/react';
// import { DecisionsPage } from '../../../pages/DecisionsPage';
// import { DecisionProvider } from '../../../providers/DecisionProvider';
// import { mockDecisions } from '../../__mocks__/decisions';

// jest.mock('../../../api/decisionsApi');

// describe('Decision Workflow', () => {
//   beforeEach(() => {
//     jest.clearAllMocks();
//   });

//   it('should display decisions and allow filtering', async () => {
//     render(
//       <DecisionProvider>
//         <DecisionsPage />
//       </DecisionProvider>
//     );

//     await waitFor(() => {
//       expect(screen.getByText(mockDecisions[0].title)).toBeInTheDocument();
//     });

//     fireEvent.change(screen.getByLabelText('Type'), { target: { value: 'quality' } });

//     await waitFor(() => {
//       const qualityDecisions = mockDecisions.filter(d => d.type === 'quality');
//       expect(screen.getAllByTestId('decision-card')).toHaveLength(qualityDecisions.length);
//     });
//   });
// });
