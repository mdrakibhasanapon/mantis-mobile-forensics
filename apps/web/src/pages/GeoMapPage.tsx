import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Case } from '../types';
import { MapPin, Navigation, Camera, ExternalLink, RefreshCw, Compass, AlertCircle } from 'lucide-react';

interface GeoMapPageProps {
  activeCase: Case | null;
}

export const GeoMapPage: React.FC<GeoMapPageProps> = ({ activeCase }) => {
  const [locations, setLocations] = useState<any[]>([]);
  const [selectedLoc, setSelectedLoc] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchLocations = () => {
    if (!activeCase) return;
    setIsLoading(true);
    api.getLocations(activeCase.id)
      .then((data) => {
        setLocations(data.locations || []);
        if (data.locations && data.locations.length > 0) {
          setSelectedLoc(data.locations[0]);
        }
      })
      .catch(console.error)
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    fetchLocations();
  }, [activeCase?.id]);

  if (!activeCase) {
    return (
      <div className="flex-1 h-full flex items-center justify-center bg-[#0c0f14] text-slate-500 text-sm">
        Select or activate a forensic case to inspect geolocation and EXIF mapping.
      </div>
    );
  }

  return (
    <div className="flex-1 h-full min-h-0 flex flex-col bg-[#0c0f14] overflow-hidden">
      {/* Top Header */}
      <div className="flex items-center justify-between p-4 border-b border-[#1c2738] bg-[#0c0f14]">
        <div>
          <div className="flex items-center space-x-2">
            <MapPin size={18} className="text-cyan-400" />
            <h2 className="text-base font-bold text-slate-100">Geolocation & EXIF Photo Intelligence</h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-400 border border-cyan-800">
              {locations.length} Geotagged Points
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Decoded GPS coordinates from media EXIF headers, cell towers, and wireless network records.
          </p>
        </div>
        <button
          onClick={fetchLocations}
          disabled={isLoading}
          className="px-3 py-1.5 rounded text-xs font-semibold bg-[#16202e] border border-[#24344a] text-cyan-300 hover:border-cyan-500/50 transition-colors flex items-center space-x-1.5"
        >
          <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
          <span>Refresh Geodata</span>
        </button>
      </div>

      {locations.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
          <Compass size={40} className="text-slate-600 mb-3" />
          <h3 className="text-sm font-semibold text-slate-300">No Geotagged Evidence Found</h3>
          <p className="text-xs text-slate-500 max-w-md mt-1">
            No image files with EXIF GPS tags or wireless coordinates have been ingested in this case yet. Ingest forensic photos (.jpg, .heic) or generate synthetic data to preview map intelligence.
          </p>
        </div>
      ) : (
        <div className="flex-1 min-h-0 flex flex-col lg:flex-row">
          {/* Left: Location Points List */}
          <div className="w-full lg:w-96 border-b lg:border-b-0 lg:border-r border-[#1c2738] overflow-y-auto bg-[#0a0e14] p-3 space-y-2">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Captured Coordinates ({locations.length})
            </div>
            {locations.map((loc) => {
              const isSelected = selectedLoc?.id === loc.id;
              return (
                <div
                  key={loc.id}
                  onClick={() => setSelectedLoc(loc)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-[#152233] border-cyan-500/70 shadow-lg shadow-cyan-950/40'
                      : 'bg-[#10151f] border-[#1c2738] hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-200">
                      <Camera size={13} className="text-cyan-400" />
                      <span className="truncate max-w-[190px]">{loc.source_file}</span>
                    </div>
                    <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-900/60">
                      {loc.latitude.toFixed(4)}, {loc.longitude.toFixed(4)}
                    </span>
                  </div>
                  {loc.camera && (
                    <div className="text-[11px] text-slate-400 mt-1 flex items-center space-x-1">
                      <span>Device:</span>
                      <span className="text-slate-300 font-medium">{loc.camera}</span>
                    </div>
                  )}
                  {loc.timestamp && (
                    <div className="text-[10px] text-slate-500 mt-1 font-mono">
                      {loc.timestamp}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Right: Map View & Detailed Point Inspector */}
          <div className="flex-1 min-h-0 flex flex-col bg-[#070a0e]">
            {selectedLoc && (
              <div className="p-3 bg-[#101724] border-b border-[#1c2738] flex flex-wrap items-center justify-between gap-3 text-xs">
                <div>
                  <span className="text-slate-400">Selected Target: </span>
                  <span className="font-bold text-slate-200">{selectedLoc.source_file}</span>
                  <span className="mx-2 text-slate-600">|</span>
                  <span className="text-slate-400">GPS: </span>
                  <span className="font-mono text-cyan-300 font-bold">
                    {selectedLoc.latitude.toFixed(6)}, {selectedLoc.longitude.toFixed(6)}
                  </span>
                  {selectedLoc.altitude && (
                    <span className="ml-2 text-slate-400">Alt: {selectedLoc.altitude}m</span>
                  )}
                </div>
                <div className="flex items-center space-x-2">
                  <a
                    href={`https://www.google.com/maps?q=${selectedLoc.latitude},${selectedLoc.longitude}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-2.5 py-1 rounded bg-[#1c293d] hover:bg-[#253652] text-cyan-300 border border-cyan-700/50 flex items-center space-x-1 text-[11px] font-semibold transition-colors"
                  >
                    <span>Google Maps</span>
                    <ExternalLink size={11} />
                  </a>
                  <a
                    href={`https://www.openstreetmap.org/?mlat=${selectedLoc.latitude}&mlon=${selectedLoc.longitude}#map=16/${selectedLoc.latitude}/${selectedLoc.longitude}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-2.5 py-1 rounded bg-[#1c293d] hover:bg-[#253652] text-emerald-300 border border-emerald-700/50 flex items-center space-x-1 text-[11px] font-semibold transition-colors"
                  >
                    <span>OpenStreetMap</span>
                    <ExternalLink size={11} />
                  </a>
                </div>
              </div>
            )}

            {/* Embedded Interactive Map */}
            <div className="flex-1 min-h-0 relative bg-[#090d14]">
              {selectedLoc ? (
                <iframe
                  title="Forensic Geolocation Map"
                  width="100%"
                  height="100%"
                  className="w-full h-full border-0 filter invert-[90%] hue-rotate-180 contrast-125"
                  src={`https://www.openstreetmap.org/export/embed.html?bbox=${selectedLoc.longitude - 0.015}%2C${selectedLoc.latitude - 0.01}%2C${selectedLoc.longitude + 0.015}%2C${selectedLoc.latitude + 0.01}&layer=mapnik&marker=${selectedLoc.latitude}%2C${selectedLoc.longitude}`}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-slate-500 text-xs">
                  Select a coordinate point from the left panel to load the interactive map view.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
