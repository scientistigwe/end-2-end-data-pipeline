// // src/decisions/__tests__/unit/utils/decisionUtils.test.ts
// import { 
//     isExpiringSoon, 
//     validateDecisionOption, 
//     calculateImpactScore 
//   } from '../../../utils/decisionUtils';
//   import { mockDecision } from '../../__mocks__/decisions';
  
//   describe('decisionUtils', () => {
//     describe('isExpiringSoon', () => {
//       it('should return true for decisions expiring within 24 hours', () => {
//         const decision = {
//           ...mockDecision,
//           deadline: new Date(Date.now() + 23 * 60 * 60 * 1000).toISOString()
//         };
//         expect(isExpiringSoon(decision)).toBe(true);
//       });
  
//       it('should return false for decisions not expiring soon', () => {
//         const decision = {
//           ...mockDecision,
//           deadline: new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString()
//         };
//         expect(isExpiringSoon(decision)).toBe(false);
//       });
//     });
  
//     describe('validateDecisionOption', () => {
//       it('should validate correct option', () => {
//         const result = validateDecisionOption(mockDecision, mockDecision.options[0].id);
//         expect(result.isValid).toBe(true);
//       });
  
//       it('should invalidate non-existent option', () => {
//         const result = validateDecisionOption(mockDecision, 'non-existent');
//         expect(result.isValid).toBe(false);
//       });
//     });
//   });