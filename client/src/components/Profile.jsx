// client/src/components/Profile.jsx
import React, { useState } from 'react';
import { AuthClient } from '../api/auth';

const Profile = () => {
  const [theme, setTheme] = useState('dark');
  const [notifications, setNotifications] = useState(true);

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      await fetch('/api/v1/users/preferences', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${new AuthClient().getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ theme, notifications_enabled: notifications }),
      });
      alert('Preferences updated!');
    } catch (error) {
      alert('Update failed: ' + error.message);
    }
  };

  return (
    <form onSubmit={handleUpdate}>
      <select value={theme} onChange={(e) => setTheme(e.target.value)}>
        <option value="dark">Dark</option>
        <option value="light">Light</option>
      </select>
      <label>
        <input
          type="checkbox"
          checked={notifications}
          onChange={(e) => setNotifications(e.target.checked)}
        />
        Enable Notifications
      </label>
      <button type="submit">Save</button>
    </form>
  );
};

export default Profile;
