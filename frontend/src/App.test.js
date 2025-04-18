import { render, screen } from '@testing-library/react';
import App from './App';
import { BrowserRouter } from 'react-router-dom';

// Mock the components that App renders to isolate testing
jest.mock('./Verification', () => () => <div data-testid="verification-component" />);
jest.mock('./Registration', () => () => <div data-testid="registration-component" />);
jest.mock('./AddStudent', () => () => <div data-testid="add-student-component" />);

test('renders app header', () => {
  render(
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );

  // Test for the app title
  const titleElement = screen.getByText(/Safe Kids Pickup Verification/i);
  expect(titleElement).toBeInTheDocument();
});

test('renders navigation links', () => {
  render(
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );

  // Test for the navigation links
  const verifyLink = screen.getByText(/Verify Guardian/i);
  const registerLink = screen.getByText(/Register Guardian/i);
  const addStudentLink = screen.getByText(/Add Student/i);

  expect(verifyLink).toBeInTheDocument();
  expect(registerLink).toBeInTheDocument();
  expect(addStudentLink).toBeInTheDocument();
});
