import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { TimelineEvent } from '../types';
import { Clock, Download, MessageSquare, PhoneCall, Globe, Shield, Calendar } from 'lucide-react';

interface TimelinePageProps {
  caseId: string;
}

export const TimelinePage: React.FC<TimelinePageProps> = ({ caseId }) => {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [eventType, setEventType] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!caseId) return;
    setIsLoading(true);
    api.listTimeline(caseId, eventType === 'all' ? undefined : eventType)
      .then(setEvents)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [caseId, eventType]);

  const handleExportCsv = () => {
    if (!caseId) return;
    window.open(api.exportTimelineCsvUrl(caseId), '_blank');
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'message':
        return <MessageSquare size={13} className="text-teal-400" />;
      case 'call':
        return <PhoneCall size={13} className="text-emerald-400" />;
      case 'web_visit':
        return <Globe size={13} className="text-cyan-400" />;
      default:
        return <Clock size={13} className="text-indigo-400" />;
    }
  };

  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts);
      if (isNaN(d.getTime())) return ts || 'N/A';
      return d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
    } catch {
      return ts || 'N/A';
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#0c0f14] overflow-hidden select-none">
      {/* Top Controls */}
      <div className="p-3 bg-[#10151f] border-b border-[#1c2738] flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-semibold text-slate-400">Filter Event Type:</span>
          {(['all', 'message', 'call', 'web_visit'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setEventType(t)}
              className={`px-3 py-1 rounded text-xs font-semibold tracking-wide transition-colors ${
                eventType === t
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#161f2e]'
              }`}
            >
              {t.toUpperCase()}
            </button>
          ))}
        </div>

        <button
          onClick={handleExportCsv}
          className="px-3 py-1.5 rounded text-xs font-semibold bg-[#172233] border border-[#26374f] text-cyan-300 hover:bg-cyan-500/20 hover:border-cyan-500/50 transition-colors flex items-center space-x-1.5"
        >
          <Download size={13} />
          <span>Export Timeline CSV</span>
        </button>
      </div>

      {/* Timeline Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2.5 font-mono text-xs">
        {isLoading ? (
          <div className="text-center py-12 text-slate-500">Reconstructing unified chronological timeline...</div>
        ) : events.length > 0 ? (
          events.map((e, idx) => (
            <div
              key={e.id}
              className="bg-[#111722] border border-[#1e2a3c] rounded p-2.5 hover:border-cyan-500/40 transition-all flex items-start space-x-3"
            >
              <div className="p-2 rounded bg-[#0b0e14] border border-[#1d2737] flex-shrink-0 mt-0.5">
                {getEventIcon(e.event_type)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-slate-100 font-sans truncate">{e.title}</span>
                  <span className="text-[11px] text-cyan-400 font-mono ml-2 whitespace-nowrap">
                    {formatTimestamp(e.timestamp_utc)}
                  </span>
                </div>
                <div className="text-slate-300 font-sans text-xs mb-1 select-text">
                  {e.description}
                </div>
                <div className="text-[10px] text-slate-500 flex items-center space-x-3 font-mono">
                  <span>Source: <code>{e.source_file}</code></span>
                  <span>Type: <strong className="text-slate-400">{e.event_type}</strong></span>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-16 text-slate-500">No events found in timeline.</div>
        )}
      </div>
    </div>
  );
};
