import React from "react";
import "./LandingPage.css";
import logo from "../assets/logo.png";

const LandingPage = ({ onLogin, onSignup }) => {
  return (
    <div className="landing-wrapper">
      <nav className="landing-nav">
        <div className="nav-logo">
          <img src={logo} alt="Matoso Logo" className="logo-img" />
        </div>
        <div className="nav-buttons">
          <button className="nav-btn btn-login" onClick={onLogin}>Login</button>
          <button className="nav-btn btn-signup" onClick={onSignup}>Sign Up</button>
        </div>
      </nav>

      <main className="landing-hero">
        <h1 className="hero-title">WELCOME TO MATOSO SMART SPACE</h1>
        <p className="hero-subtitle">A little help for big minds</p>
      </main>

      {/* ── Static Illustrative Forest Scene ── */}
      <div className="forest-scene">
        <svg className="forest-svg" viewBox="0 0 1440 220" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMax slice">

          {/* ── Sky / Background Hills ── */}
          <ellipse cx="720" cy="260" rx="900" ry="120" fill="#81C784" opacity="0.4"/>

          {/* ── Ground ── */}
          <rect x="0" y="160" width="1440" height="60" fill="#388E3C"/>
          <ellipse cx="720" cy="160" rx="800" ry="30" fill="#4CAF50"/>

          {/* ── Background Trees (darker, smaller = depth) ── */}
          {/* Tree far left */}
          <polygon points="60,160 90,80 120,160" fill="#1B5E20"/>
          <polygon points="70,160 90,100 110,160" fill="#2E7D32"/>
          <rect x="84" y="148" width="12" height="15" fill="#5D4037"/>

          {/* Tree far right */}
          <polygon points="1320,160 1350,80 1380,160" fill="#1B5E20"/>
          <polygon points="1330,160 1350,100 1370,160" fill="#2E7D32"/>
          <rect x="1344" y="148" width="12" height="15" fill="#5D4037"/>

          {/* ── Middle Ground Trees ── */}
          {/* Tree 1 */}
          <polygon points="150,165 195,60 240,165" fill="#2E7D32"/>
          <polygon points="162,165 195,85 228,165" fill="#388E3C"/>
          <rect x="188" y="150" width="14" height="18" fill="#4E342E"/>

          {/* Tree 2 - pine */}
          <polygon points="310,165 340,70 370,165" fill="#1B5E20"/>
          <polygon points="305,155 340,90 375,155" fill="#2E7D32"/>
          <polygon points="315,140 340,110 365,140" fill="#388E3C"/>
          <rect x="334" y="152" width="12" height="16" fill="#4E342E"/>

          {/* Tree 3 - round */}
          <circle cx="470" cy="115" r="45" fill="#388E3C"/>
          <circle cx="450" cy="125" r="35" fill="#2E7D32"/>
          <circle cx="490" cy="120" r="38" fill="#43A047"/>
          <rect x="463" y="150" width="14" height="18" fill="#4E342E"/>

          {/* Tree 4 - tall */}
          <polygon points="590,165 625,50 660,165" fill="#1B5E20"/>
          <polygon points="600,165 625,75 650,165" fill="#2E7D32"/>
          <polygon points="610,148 625,100 640,148" fill="#388E3C"/>
          <rect x="618" y="153" width="14" height="15" fill="#4E342E"/>

          {/* Tree 5 - big center */}
          <circle cx="720" cy="100" r="55" fill="#2E7D32"/>
          <circle cx="695" cy="115" r="42" fill="#388E3C"/>
          <circle cx="745" cy="110" r="45" fill="#43A047"/>
          <circle cx="720" cy="95"  r="40" fill="#4CAF50"/>
          <rect x="712" y="148" width="16" height="20" fill="#4E342E"/>

          {/* Tree 6 - pine */}
          <polygon points="810,165 845,60 880,165" fill="#1B5E20"/>
          <polygon points="815,155 845,80 875,155" fill="#2E7D32"/>
          <polygon points="820,138 845,105 870,138" fill="#388E3C"/>
          <rect x="838" y="153" width="14" height="15" fill="#4E342E"/>

          {/* Tree 7 - round */}
          <circle cx="960" cy="118" r="42" fill="#2E7D32"/>
          <circle cx="940" cy="128" r="33" fill="#388E3C"/>
          <circle cx="978" cy="122" r="36" fill="#43A047"/>
          <rect x="952" y="151" width="14" height="17" fill="#4E342E"/>

          {/* Tree 8 */}
          <polygon points="1060,165 1095,65 1130,165" fill="#1B5E20"/>
          <polygon points="1068,165 1095,88 1122,165" fill="#2E7D32"/>
          <rect x="1088" y="152" width="14" height="16" fill="#4E342E"/>

          {/* Tree 9 */}
          <circle cx="1230" cy="112" r="48" fill="#388E3C"/>
          <circle cx="1208" cy="122" r="36" fill="#2E7D32"/>
          <circle cx="1250" cy="118" r="40" fill="#43A047"/>
          <rect x="1223" y="150" width="14" height="18" fill="#4E342E"/>

          {/* ── Giraffe ── */}
          <g transform="translate(240, 75)">
            {/* body */}
            <ellipse cx="25" cy="75" rx="18" ry="25" fill="#F9A825"/>
            {/* neck */}
            <rect x="28" y="30" width="10" height="45" fill="#F9A825"/>
            {/* head */}
            <ellipse cx="33" cy="25" rx="12" ry="10" fill="#F9A825"/>
            {/* horns */}
            <rect x="27" y="12" width="4" height="10" fill="#8D6E63"/>
            <rect x="35" y="12" width="4" height="10" fill="#8D6E63"/>
            {/* eye */}
            <circle cx="38" cy="22" r="2.5" fill="#333"/>
            {/* legs */}
            <rect x="10" y="95" width="7" height="25" fill="#F57F17"/>
            <rect x="20" y="95" width="7" height="25" fill="#F57F17"/>
            <rect x="32" y="95" width="7" height="25" fill="#F57F17"/>
            <rect x="42" y="95" width="7" height="25" fill="#F57F17"/>
            {/* spots */}
            <ellipse cx="20" cy="70" rx="5" ry="7" fill="#E65100" opacity="0.5"/>
            <ellipse cx="33" cy="80" rx="4" ry="6" fill="#E65100" opacity="0.5"/>
          </g>

          {/* ── Elephant ── */}
          <g transform="translate(380, 100)">
            {/* body */}
            <ellipse cx="40" cy="55" rx="38" ry="30" fill="#90A4AE"/>
            {/* head */}
            <circle cx="15" cy="38" r="22" fill="#90A4AE"/>
            {/* trunk */}
            <path d="M8,55 Q0,75 10,85" stroke="#78909C" stroke-width="8" fill="none" stroke-linecap="round"/>
            {/* ear */}
            <ellipse cx="0" cy="38" rx="12" ry="18" fill="#78909C"/>
            {/* eye */}
            <circle cx="20" cy="32" r="3" fill="#333"/>
            {/* tusk */}
            <path d="M10,50 Q5,58 12,62" stroke="ivory" stroke-width="4" fill="none"/>
            {/* legs */}
            <rect x="10" y="78" width="14" height="22" rx="4" fill="#78909C"/>
            <rect x="28" y="78" width="14" height="22" rx="4" fill="#78909C"/>
            <rect x="46" y="78" width="14" height="22" rx="4" fill="#78909C"/>
            <rect x="62" y="78" width="14" height="22" rx="4" fill="#78909C"/>
          </g>

          {/* ── Lion ── */}
          <g transform="translate(560, 110)">
            {/* mane */}
            <circle cx="28" cy="28" r="24" fill="#E65100"/>
            {/* body */}
            <ellipse cx="55" cy="42" rx="30" ry="18" fill="#FFA726"/>
            {/* head */}
            <circle cx="28" cy="28" r="18" fill="#FFA726"/>
            {/* ears */}
            <polygon points="14,14 10,4 22,12" fill="#FFA726"/>
            <polygon points="38,14 42,4 32,12" fill="#FFA726"/>
            {/* eyes */}
            <circle cx="22" cy="25" r="3" fill="#333"/>
            <circle cx="34" cy="25" r="3" fill="#333"/>
            {/* nose */}
            <ellipse cx="28" cy="33" rx="4" ry="3" fill="#E91E63"/>
            {/* legs */}
            <rect x="32" y="54" width="10" height="18" rx="3" fill="#FFA726"/>
            <rect x="46" y="54" width="10" height="18" rx="3" fill="#FFA726"/>
            <rect x="60" y="54" width="10" height="18" rx="3" fill="#FFA726"/>
            <rect x="74" y="54" width="10" height="18" rx="3" fill="#FFA726"/>
            {/* tail */}
            <path d="M85,38 Q105,30 100,50" stroke="#FFA726" stroke-width="5" fill="none"/>
            <circle cx="100" cy="52" r="6" fill="#E65100"/>
          </g>

          {/* ── Zebra ── */}
          <g transform="translate(780, 105)">
            {/* body */}
            <ellipse cx="40" cy="50" rx="32" ry="20" fill="white"/>
            {/* head */}
            <ellipse cx="12" cy="36" rx="16" ry="14" fill="white"/>
            {/* mane */}
            <path d="M10,22 Q20,18 28,22 Q20,28 10,22" fill="#333"/>
            {/* snout */}
            <ellipse cx="5" cy="40" rx="8" ry="6" fill="#eee"/>
            {/* eye */}
            <circle cx="16" cy="32" r="3" fill="#333"/>
            {/* stripes body */}
            <path d="M20,32 Q25,50 20,68" stroke="#333" stroke-width="4" fill="none"/>
            <path d="M30,30 Q36,50 32,70" stroke="#333" stroke-width="4" fill="none"/>
            <path d="M42,30 Q48,50 44,70" stroke="#333" stroke-width="4" fill="none"/>
            <path d="M54,32 Q58,50 55,68" stroke="#333" stroke-width="4" fill="none"/>
            {/* stripes head */}
            <path d="M6,28 Q12,36 6,44" stroke="#333" stroke-width="3" fill="none"/>
            {/* legs */}
            <rect x="16" y="65" width="10" height="22" rx="3" fill="white"/>
            <line x1="16" x2="26" y1="72" y2="72" stroke="#333" stroke-width="2"/>
            <rect x="30" y="65" width="10" height="22" rx="3" fill="white"/>
            <line x1="30" x2="40" y1="72" y2="72" stroke="#333" stroke-width="2"/>
            <rect x="44" y="65" width="10" height="22" rx="3" fill="white"/>
            <rect x="58" y="65" width="10" height="22" rx="3" fill="white"/>
          </g>

          {/* ── Parrot on branch ── */}
          <g transform="translate(1020, 60)">
            {/* branch */}
            <path d="M0,40 Q40,35 80,40" stroke="#5D4037" stroke-width="6" fill="none"/>
            {/* body */}
            <ellipse cx="30" cy="28" rx="12" ry="16" fill="#43A047"/>
            {/* head */}
            <circle cx="30" cy="12" r="11" fill="#E53935"/>
            {/* beak */}
            <polygon points="38,14 48,18 38,20" fill="#FFA726"/>
            {/* eye */}
            <circle cx="35" cy="10" r="3" fill="#333"/>
            <circle cx="36" cy="9" r="1" fill="white"/>
            {/* wing */}
            <ellipse cx="20" cy="28" rx="8" ry="14" fill="#1565C0"/>
            {/* tail */}
            <path d="M30,42 Q25,60 20,70" stroke="#1565C0" stroke-width="5" fill="none"/>
            <path d="M30,42 Q30,62 30,72" stroke="#43A047" stroke-width="5" fill="none"/>
            {/* feet */}
            <line x1="26" y1="42" x2="20" y2="50" stroke="#FFA726" stroke-width="3"/>
            <line x1="34" y1="42" x2="40" y2="50" stroke="#FFA726" stroke-width="3"/>
          </g>

          {/* ── Butterfly ── */}
          <g transform="translate(1150, 55)">
            {/* wings */}
            <ellipse cx="10" cy="20" rx="18" ry="12" fill="#CE93D8" opacity="0.9" transform="rotate(-20,10,20)"/>
            <ellipse cx="40" cy="20" rx="18" ry="12" fill="#CE93D8" opacity="0.9" transform="rotate(20,40,20)"/>
            <ellipse cx="12" cy="30" rx="12" ry="8"  fill="#AB47BC" opacity="0.9" transform="rotate(20,12,30)"/>
            <ellipse cx="38" cy="30" rx="12" ry="8"  fill="#AB47BC" opacity="0.9" transform="rotate(-20,38,30)"/>
            {/* body */}
            <ellipse cx="25" cy="25" rx="4" ry="12" fill="#4A148C"/>
            {/* antennae */}
            <path d="M22,14 Q15,5 12,2" stroke="#4A148C" stroke-width="1.5" fill="none"/>
            <path d="M28,14 Q35,5 38,2" stroke="#4A148C" stroke-width="1.5" fill="none"/>
            <circle cx="12" cy="2" r="2.5" fill="#4A148C"/>
            <circle cx="38" cy="2" r="2.5" fill="#4A148C"/>
          </g>

          {/* ── Monkey on tree ── */}
          <g transform="translate(1090, 90)">
            {/* body */}
            <ellipse cx="20" cy="45" rx="14" ry="18" fill="#795548"/>
            {/* head */}
            <circle cx="20" cy="24" r="14" fill="#795548"/>
            {/* face */}
            <ellipse cx="20" cy="28" rx="9" ry="7" fill="#FFCC80"/>
            {/* ears */}
            <circle cx="6"  cy="22" r="6" fill="#795548"/>
            <circle cx="34" cy="22" r="6" fill="#795548"/>
            <circle cx="6"  cy="22" r="3" fill="#FFCC80"/>
            <circle cx="34" cy="22" r="3" fill="#FFCC80"/>
            {/* eyes */}
            <circle cx="15" cy="20" r="3" fill="#333"/>
            <circle cx="25" cy="20" r="3" fill="#333"/>
            {/* nose */}
            <ellipse cx="20" cy="27" rx="3" ry="2" fill="#5D4037"/>
            {/* arms */}
            <path d="M6,40 Q-5,50 0,60"  stroke="#795548" stroke-width="7" fill="none" stroke-linecap="round"/>
            <path d="M34,40 Q45,50 40,60" stroke="#795548" stroke-width="7" fill="none" stroke-linecap="round"/>
            {/* legs */}
            <path d="M12,60 Q8,72 12,80"  stroke="#795548" stroke-width="7" fill="none" stroke-linecap="round"/>
            <path d="M28,60 Q32,72 28,80" stroke="#795548" stroke-width="7" fill="none" stroke-linecap="round"/>
            {/* tail */}
            <path d="M34,55 Q55,50 50,35" stroke="#795548" stroke-width="5" fill="none" stroke-linecap="round"/>
          </g>

          {/* ── Foreground grass tufts ── */}
          <path d="M0,165 Q10,150 20,165"   stroke="#2E7D32" stroke-width="3" fill="none"/>
          <path d="M30,165 Q40,148 50,165"  stroke="#2E7D32" stroke-width="3" fill="none"/>
          <path d="M200,162 Q210,148 220,162" stroke="#388E3C" stroke-width="3" fill="none"/>
          <path d="M500,163 Q510,148 520,163" stroke="#2E7D32" stroke-width="3" fill="none"/>
          <path d="M900,163 Q910,148 920,163" stroke="#388E3C" stroke-width="3" fill="none"/>
          <path d="M1200,162 Q1210,148 1220,162" stroke="#2E7D32" stroke-width="3" fill="none"/>
          <path d="M1400,165 Q1415,148 1430,165" stroke="#388E3C" stroke-width="3" fill="none"/>

          {/* ── Sun ── */}
          <circle cx="1380" cy="30" r="28" fill="#FDD835" opacity="0.9"/>
          <circle cx="1380" cy="30" r="20" fill="#FFEE58"/>

          {/* ── Clouds ── */}
          <g opacity="0.85">
            <ellipse cx="200" cy="30" rx="55" ry="22" fill="white"/>
            <ellipse cx="170" cy="38" rx="35" ry="20" fill="white"/>
            <ellipse cx="235" cy="35" rx="38" ry="18" fill="white"/>
          </g>
          <g opacity="0.8">
            <ellipse cx="700" cy="20" rx="60" ry="20" fill="white"/>
            <ellipse cx="670" cy="28" rx="38" ry="18" fill="white"/>
            <ellipse cx="735" cy="25" rx="40" ry="16" fill="white"/>
          </g>

        </svg>
      </div>
    </div>
  );
};

export default LandingPage;