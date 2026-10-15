import React from 'react';
import { Mail, MessageCircle, Camera, Search, PhoneCall } from 'lucide-react';

export const AccountCards: React.FC = () => {
  const accounts = [
    {
      id: 'ig-1',
      name: 'eritynydera_',
      handle: 'eritynydera_...',
      icon: Camera,
      color: 'from-pink-500 to-rose-500',
      date: 'Wed, 18 Jun 2025, 5:14:34 pm GMT+5:30',
      lastActivity: 'Bolbo log ho',
      version: 'Not Available',
      bio: 'Everyone on and off the phone!',
    },
    {
      id: 'gm-1',
      name: 'officeryaswa',
      handle: 'officeryaswa@gmail.com',
      icon: Mail,
      color: 'from-red-500 to-amber-500',
      date: 'Fri, 20 Jun 2025, 3:03:07 pm GMT+5:30',
      lastActivity: 'SIDCC',
      version: 'Not Available',
      bio: 'Not Available',
    },
    {
      id: 'wa-1',
      name: 'galadass',
      handle: '15457845211@s.whatsapp.net',
      icon: MessageCircle,
      color: 'from-emerald-500 to-green-600',
      date: 'Fri, 20 Jun 2025, 3:12:02 pm GMT+5:30',
      lastActivity: 'SIDCC',
      version: 'Not Available',
      bio: 'Not Available',
    },
    {
      id: 'goog-1',
      name: 'Google search default account',
      handle: 'google_search_default_account',
      icon: Search,
      color: 'from-blue-500 to-cyan-500',
      date: 'Unknown time',
      lastActivity: 'Not Available',
      version: 'Not Available',
      bio: 'Not Available',
    },
    {
      id: 'wa-2',
      name: 'galadass',
      handle: '15457845211@s.whatsapp.net',
      icon: MessageCircle,
      color: 'from-emerald-500 to-green-600',
      date: 'Fri, 20 Jun 2025, 3:12:02 pm GMT+5:30',
      lastActivity: 'Not Available',
      version: 'Not Available',
      bio: 'Hey there! I am using WhatsApp.',
    },
    {
      id: 'wa-3',
      name: 'Jackie',
      handle: '23178206975@s.whatsapp.net',
      icon: MessageCircle,
      color: 'from-emerald-500 to-green-600',
      date: 'Fri, 20 Jun 2025, 3:25:46 pm GMT+5:30',
      lastActivity: 'Team India Playing XI for the 1st Test vs...',
      version: 'Not Available',
      bio: 'Team India Playing XI for the 1st Test (e...',
    },
    {
      id: 'tel-1',
      name: '060345787877',
      handle: '063845787877',
      icon: PhoneCall,
      color: 'from-emerald-500 to-teal-600',
      date: 'Thu, 20 Mar 2025, 1:44:15 pm GMT+5:30',
      lastActivity: 'Outgoing call to +22231232585785 was not answered.',
      version: 'Not Available',
      bio: 'Not Available',
    },
    {
      id: 'wa-4',
      name: 'Jackie',
      handle: '23178206975@s.whatsapp.net',
      icon: MessageCircle,
      color: 'from-emerald-500 to-green-600',
      date: 'Fri, 20 Jun 2025, 3:25:46 pm GMT+5:30',
      lastActivity: 'Team India Playing XI for the 1st Test vs...',
      version: 'Not Available',
      bio: 'Team India Playing XI for the 1st Test (e...',
    },
  ];

  return (
    <div className="mb-3">
      <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center justify-between">
        <span>Accounts</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
        {accounts.map((acc) => {
          const Icon = acc.icon;
          return (
            <div
              key={acc.id}
              className="bg-[#111722] border border-[#1e2a3c] hover:border-cyan-500/40 rounded-md p-2.5 transition-all text-xs"
            >
              <div className="flex items-start justify-between mb-1.5">
                <div className="flex items-center space-x-2 min-w-0">
                  <div className={`w-6 h-6 rounded-full bg-gradient-to-tr ${acc.color} flex items-center justify-center text-white text-[10px] flex-shrink-0`}>
                    <Icon size={13} />
                  </div>
                  <div className="truncate">
                    <div className="font-semibold text-slate-100 text-[11px] truncate leading-tight">{acc.name}</div>
                    <div className="text-[10px] text-slate-400 font-mono truncate">{acc.handle}</div>
                  </div>
                </div>
                <div className="text-[9px] text-slate-500 font-mono flex-shrink-0 ml-2 whitespace-nowrap">{acc.date}</div>
              </div>

              <div className="bg-[#0b1017] rounded p-1.5 border border-[#192230] text-[10px] space-y-0.5 font-mono">
                <div className="truncate">
                  <span className="text-slate-500">Last Activity: </span>
                  <span className="text-cyan-300">{acc.lastActivity}</span>
                </div>
                <div>
                  <span className="text-slate-500">Version: </span>
                  <span className="text-slate-400">{acc.version}</span>
                </div>
                <div className="truncate">
                  <span className="text-slate-500">Bio: </span>
                  <span className="text-slate-300">{acc.bio}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
