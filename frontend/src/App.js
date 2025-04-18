import React from 'react';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  NavLink
} from 'react-router-dom';
import Verification from './Verification';
import Registration from './Registration';
import AddStudent from './AddStudent'; // Import the new component
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <header className="App-header">
          <h1>Safe Kids Pickup Verification</h1>
          <nav>
            {/* Use NavLink for active styling */}
            <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>Verify Guardian</NavLink>
            <NavLink to="/register" className={({ isActive }) => isActive ? 'active' : ''}>Register Guardian</NavLink>
            <NavLink to="/add-student" className={({ isActive }) => isActive ? 'active' : ''}>Add Student</NavLink> {/* Add link */}
          </nav>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Verification />} />
            <Route path="/register" element={<Registration />} />
            <Route path="/add-student" element={<AddStudent />} /> {/* Add route */}
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
