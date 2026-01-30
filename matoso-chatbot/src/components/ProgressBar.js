import React from 'react';

function ProgressBar({ value, max }) {
  const percent = Math.round((value / max) * 100);

  return (
    <div style={{ width: '100%', margin: '4px 0' }}>
      <label style={{ fontWeight: 500, fontSize: '13px', color: '#9a9ba7' }}>
        Session progress {value}/{max}
      </label>
      <div
        style={{
          height: '8px',
          width: '100%',
          backgroundColor: '#2a2b32',
          borderRadius: '18px',
          marginTop: '6px',
          boxShadow: 'inset 0 1px 4px rgba(0, 0, 0, 0.35)'
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${percent}%`,
            backgroundColor: '#10a37f',
            borderRadius: '18px',
            transition: 'width 0.5s'
          }}
        ></div>
      </div>
    </div>
  );
}

export default ProgressBar;
