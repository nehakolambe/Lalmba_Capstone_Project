import React from 'react';

function ProgressBar({ value, max, darkMode = false, label = 'Session progress' }) {
  const percent = Math.round((value / max) * 100);

  return (
    <div style={{ width: '100%', margin: '4px 0' }}>
      <label style={{
        fontWeight: 500,
        fontSize: '13px',
        color: darkMode ? '#9a9ba7' : '#666'
      }}>
        {label} {value}/{max}
      </label>

  
      <div style={{
        height: '14px',
        width: '100%',
        backgroundColor: darkMode ? '#2a2b32' : '#e0e0e0',
        borderRadius: '18px',
        marginTop: '6px',
        boxShadow: 'inset 0 1px 4px rgba(0,0,0,0.2)',
        position: 'relative',
        overflow: 'visible',
      }}>
    
        <div style={{
          height: '100%',
          width: `${percent}%`,
          background: darkMode
            ? 'linear-gradient(90deg, #1a3a5c, #4a90d9)'   
            : 'linear-gradient(90deg, #228B22, #66BB6A)',   
          borderRadius: '18px',
          transition: 'width 0.5s ease',
          position: 'relative',
        }}>
    
          {percent > 0 && (
            <div style={{
              position: 'absolute',
              right: '-22px',
              top: '50%',
              transform: 'translateY(-50%)',
              fontSize: '2rem',
              filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))',
              transition: 'right 0.5s ease',
              userSelect: 'none',
            }}>
              {darkMode ? '🚀' : '🪁'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ProgressBar;
