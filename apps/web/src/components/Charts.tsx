import React, { useState } from 'react';
import { Phone, MessageSquare } from 'lucide-react';

export const Charts: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'CONTACTS' | 'GROUPS' | 'CALLS'>('CONTACTS');

  const topContacts = [
    { name: 'Ps2', shortName: 'Ps2', total: 4645, calls: 14, msgs: 4631, color: '#06b6d4' },
    { name: '05765586706756', shortName: '0576...', total: 3598, calls: 38, msgs: 3560, color: '#f59e0b' },
    { name: '0757666370755', shortName: '0757...', total: 1544, calls: 0, msgs: 1544, color: '#10b981' },
    { name: 'Rose', shortName: 'Rose', total: 1318, calls: 18, msgs: 1300, color: '#f43f5e' },
    { name: '534345345345354', shortName: '5343...', total: 1019, calls: 19, msgs: 1000, color: '#8b5cf6' },
    { name: 'Jackie', shortName: 'Jackie', total: 1000, calls: 0, msgs: 1000, color: '#ec4899' },
    { name: 'MR JOHNSON', shortName: 'MR JOHNSON', total: 948, calls: 0, msgs: 948, color: '#38bdf8' },
    { name: 'azrplap', shortName: 'azrplap', total: 597, calls: 0, msgs: 597, color: '#84cc16' },
    { name: 'Jackie', shortName: 'Jackie', total: 577, calls: 28, msgs: 549, color: '#eab308' },
    { name: 'NoorinImroz', shortName: 'NoorinImroz', total: 481, calls: 0, msgs: 481, color: '#2dd4bf' },
  ];

  // SVG Donut calculation
  const totalSum = topContacts.reduce((acc, c) => acc + c.total, 0);
  let cumulativeAngle = 0;
  const radius = 62;
  const strokeWidth = 22;
  const center = 85;

  const maxVal = topContacts[0].total;

  return (
    <div className="bg-[#111722] border border-[#1e2a3c] rounded-md p-3 shadow-md">
      {/* Sub tabs: CONTACTS, GROUPS, CALLS */}
      <div className="flex items-center space-x-1.5 mb-3 border-b border-[#1c2738] pb-2">
        {(['CONTACTS', 'GROUPS', 'CALLS'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-1 text-[11px] font-bold rounded transition-colors tracking-wide ${
              activeTab === tab
                ? 'bg-[#182334] text-cyan-400 border border-cyan-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
        Contacts (Top 10)
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
        {/* Left: Donut Chart & Breakdown Legend */}
        <div className="lg:col-span-7 flex flex-col sm:flex-row items-center gap-6">
          <div className="flex-shrink-0 relative">
            <svg width="170" height="170" viewBox="0 0 170 170" className="transform -rotate-90">
              {topContacts.map((c, i) => {
                const fraction = c.total / totalSum;
                const dashArray = 2 * Math.PI * radius;
                const dashOffset = dashArray * (1 - fraction);
                const rotation = (cumulativeAngle / totalSum) * 360;
                cumulativeAngle += c.total;

                return (
                  <circle
                    key={i}
                    cx={center}
                    cy={center}
                    r={radius}
                    fill="transparent"
                    stroke={c.color}
                    strokeWidth={strokeWidth}
                    strokeDasharray={dashArray}
                    strokeDashoffset={dashOffset}
                    transform={`rotate(${rotation} ${center} ${center})`}
                    className="hover:opacity-80 transition-opacity cursor-pointer"
                  >
                    <title>{`${c.name}: ${c.total} (${c.calls} calls / ${c.msgs} messages)`}</title>
                  </circle>
                );
              })}
            </svg>
          </div>

          {/* Contact breakdown list matching reference layout */}
          <div className="flex-1 w-full space-y-1 text-xs font-mono">
            {topContacts.map((c, i) => (
              <div key={i} className="flex items-center justify-between py-0.5 border-b border-[#182232]/60 text-[11px]">
                <div className="flex items-center space-x-2 min-w-0">
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: c.color }} />
                  <span className="text-slate-300 truncate" title={c.name}>{c.name}</span>
                </div>
                <div className="text-slate-400 flex items-center space-x-1.5 flex-shrink-0 ml-2">
                  <span className="font-semibold text-slate-200">{c.total}</span>
                  <span className="text-slate-500 text-[10px]">(&#128222; {c.calls} / &#128172; {c.msgs})</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Comparative Bar Chart ("ACTIVITY DISTRIBUTION") */}
        <div className="lg:col-span-5 border-t lg:border-t-0 lg:border-l border-[#1c2738] pt-3 lg:pt-0 lg:pl-4">
          <div className="flex items-center justify-between text-[10px] text-slate-400 mb-2 font-mono">
            <span className="font-bold tracking-wider uppercase text-slate-300">ACTIVITY DISTRIBUTION</span>
            <div className="flex items-center space-x-3">
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
                <span>Calls</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                <span>Messages</span>
              </span>
            </div>
          </div>

          {/* Bar Chart Container with reference gridlines */}
          <div className="h-44 bg-[#0c1017] rounded border border-[#192332] p-2 flex flex-col justify-between relative select-none">
            {/* Gridlines */}
            <div className="absolute inset-0 p-2 pointer-events-none flex flex-col justify-between text-[8px] text-slate-600 font-mono">
              <div className="border-b border-dashed border-[#1f293d]/50 w-full flex justify-between"><span>1.0</span></div>
              <div className="border-b border-dashed border-[#1f293d]/50 w-full flex justify-between"><span>0.75</span></div>
              <div className="border-b border-dashed border-[#1f293d]/50 w-full flex justify-between"><span>0.5</span></div>
              <div className="border-b border-dashed border-[#1f293d]/50 w-full flex justify-between"><span>0.25</span></div>
              <div className="w-full flex justify-between"><span>0</span></div>
            </div>

            {/* 10 Vertical Bars */}
            <div className="flex-1 flex items-end justify-between gap-1 z-10 pt-4 pb-1 px-4">
              {topContacts.map((c, idx) => {
                const heightPercent = Math.max(14, Math.round((c.total / maxVal) * 90));
                return (
                  <div
                    key={idx}
                    className="flex-1 flex flex-col items-center h-full justify-end cursor-pointer group"
                    title={`${c.name}: ${c.total} total (${c.calls} calls, ${c.msgs} messages)`}
                  >
                    <div
                      className="w-full max-w-[20px] rounded-t transition-all group-hover:brightness-125"
                      style={{
                        height: `${heightPercent}%`,
                        backgroundColor: c.color,
                        opacity: 0.9,
                      }}
                    />
                    <span className="text-[8px] text-slate-400 truncate w-full text-center mt-1 font-mono">
                      {c.shortName}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
