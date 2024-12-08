// // src/decisions/__tests__/e2e/decisions.cy.ts
// describe('Decisions E2E', () => {
//     beforeEach(() => {
//       cy.intercept('GET', '/api/decisions*', { fixture: 'decisions.json' }).as('getDecisions');
//       cy.visit('/decisions');
//     });
  
//     it('should load and display decisions', () => {
//       cy.wait('@getDecisions');
//       cy.get('[data-testid=decision-card]').should('have.length.gt', 0);
//     });
  
//     it('should filter decisions', () => {
//       cy.wait('@getDecisions');
//       cy.get('select[name=type]').select('quality');
//       cy.get('[data-testid=decision-card]').should('have.length.gt', 0);
//     });
  
//     it('should navigate to decision details', () => {
//       cy.wait('@getDecisions');
//       cy.get('[data-testid=decision-card]').first().click();
//       cy.url().should('include', '/decisions/');
//     });
//   });