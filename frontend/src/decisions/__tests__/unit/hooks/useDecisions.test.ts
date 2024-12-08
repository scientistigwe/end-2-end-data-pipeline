// // src/decisions/__tests__/unit/hooks/useDecisions.test.ts
// import { renderHook, act } from '@testing-library/react-hooks';
// import { useDecisions } from '../../../hooks/useDecisions';
// import { decisionsApi } from '../../../api/decisionsApi';
// import { mockDecisions } from '../../__mocks__/decisions';

// jest.mock('../../../api/decisionsApi');

// describe('useDecisions', () => {
//   beforeEach(() => {
//     jest.clearAllMocks();
//   });

//   it('should fetch decisions on mount', async () => {
//     (decisionsApi.listDecisions as jest.Mock).mockResolvedValueOnce({ data: mockDecisions });

//     const { result, waitForNextUpdate } = renderHook(() => useDecisions('pipeline-1'));
    
//     expect(result.current.isLoading).toBe(true);
//     await waitForNextUpdate();
    
//     expect(result.current.decisions).toEqual(mockDecisions);
//     expect(result.current.isLoading).toBe(false);
//   });

//   it('should handle decision making', async () => {
//     const updatedDecision = { ...mockDecisions[0], status: 'completed' };
//     (decisionsApi.makeDecision as jest.Mock).mockResolvedValueOnce({ data: updatedDecision });

//     const { result } = renderHook(() => useDecisions('pipeline-1'));

//     await act(async () => {
//       await result.current.makeDecision('decision-1', 'option-1');
//     });

//     expect(decisionsApi.makeDecision).toHaveBeenCalledWith('decision-1', 'option-1', undefined);
//   });
// });




