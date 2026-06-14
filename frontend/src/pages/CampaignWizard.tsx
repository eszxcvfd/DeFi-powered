import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createCampaign } from "@/api/campaigns";
import { listRunnableSources, setCampaignSources } from "@/api/connectors";
import type { RunnableSource } from "@/types/connector";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DEFAULT_SCORING_WEIGHTS, SCORING_LABELS } from "@/constants/scoring";
import type { CampaignCreatePayload, IcpCriteria } from "@/types/campaign";

const STEPS = [
  "Objective",
  "Industry & keywords",
  "ICP",
  "Market & dates",
  "Sources",
  "Scoring weights",
  "Review",
] as const;

const emptyIcp = (): IcpCriteria => ({
  industry: "",
  organization_type: "",
  company_size: "",
  role_or_title_targets: [],
  country_or_region: "",
  pain_points: [],
  use_cases: [],
  positive_keywords: [],
  excluded_keywords: [],
});

function splitCsv(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export default function CampaignWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [targetIndustry, setTargetIndustry] = useState("");
  const [productFocus, setProductFocus] = useState("");
  const [positiveKw, setPositiveKw] = useState("");
  const [excludeKw, setExcludeKw] = useState("");
  const [icp, setIcp] = useState<IcpCriteria>(emptyIcp);
  const [regions, setRegions] = useState("");
  const [languages, setLanguages] = useState("en");
  const [timezone, setTimezone] = useState("UTC");
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [weights, setWeights] = useState({ ...DEFAULT_SCORING_WEIGHTS });
  const [sources, setSources] = useState<RunnableSource[]>([]);
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);

  useEffect(() => {
    if (step === 4) {
      listRunnableSources().then(setSources).catch(() => setSources([]));
    }
  }, [step]);

  const payload = (): CampaignCreatePayload => ({
    name,
    description,
    target_industry: targetIndustry,
    product_or_service_focus: productFocus,
    market_regions: splitCsv(regions),
    languages: splitCsv(languages),
    timezone,
    date_range: { start: dateStart || null, end: dateEnd || null },
    positive_keywords: splitCsv(positiveKw),
    exclude_keywords: splitCsv(excludeKw),
    icp,
    scoring_weights: weights,
  });

  async function save() {
    setSaving(true);
    try {
      const created = await createCampaign(payload());
      if (selectedSourceIds.length) {
        await setCampaignSources(created.id, selectedSourceIds);
      }
      navigate(`/campaigns/${created.id}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="p-8 max-w-4xl mx-auto" data-testid="campaign-wizard">
      <div className="border-b border-slate-200 pb-5 mb-6">
        <span className="text-[10px] font-mono uppercase tracking-widest text-[var(--color-muted)] bg-slate-100 px-2 py-0.5 rounded-sm">Step {step + 1} of {STEPS.length}</span>
        <h1 className="text-xl font-bold tracking-tight text-slate-900 mt-2">Create Discovery Pipeline</h1>
        <p className="text-xs text-[var(--color-muted)] mt-1">Configure criteria, targeting data, sources and matching priorities.</p>
      </div>

      {/* Progress Timeline Tracker (Sharp & Minimalist) */}
      <div className="mb-8 overflow-x-auto pb-2">
        <div className="flex items-center min-w-[600px] gap-1 text-[10px] font-mono uppercase tracking-wider">
          {STEPS.map((label, i) => (
            <div key={label} className="flex items-center flex-1 last:flex-none">
              <span className={`inline-flex items-center justify-center size-5 border font-semibold rounded-sm mr-2 ${
                i === step
                  ? "bg-slate-900 text-white border-slate-900"
                  : i < step
                  ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                  : "bg-white text-slate-400 border-slate-200"
              }`}>
                {i + 1}
              </span>
              <span className={i === step ? "text-slate-900 font-bold" : i < step ? "text-emerald-700 font-semibold" : "text-slate-400"}>
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <span className="h-[1px] bg-slate-200 flex-1 mx-3 min-w-[20px]"></span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Form Area */}
      <div className="bg-white border border-slate-200 p-6 rounded-sm min-h-[300px] flex flex-col justify-between">
        <div className="space-y-4">
          {step === 0 && (
            <div className="grid grid-cols-1 gap-4 max-w-lg">
              <div>
                <Label htmlFor="name" className="text-xs font-bold text-slate-700">Campaign Name</Label>
                <Input id="name" data-testid="wizard-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. DeFi RWA Partnership Discovery" className="mt-1" />
              </div>
              <div>
                <Label htmlFor="desc" className="text-xs font-bold text-slate-700">Description</Label>
                <Input id="desc" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Describe the market segment or main goals" className="mt-1" />
              </div>
            </div>
          )}
          {step === 1 && (
            <div className="grid grid-cols-1 gap-4 max-w-lg">
              <div>
                <Label className="text-xs font-bold text-slate-700">Target Industry</Label>
                <Input data-testid="wizard-industry" value={targetIndustry} onChange={(e) => setTargetIndustry(e.target.value)} placeholder="e.g. Tokenization, Fintech" className="mt-1" />
              </div>
              <div>
                <Label className="text-xs font-bold text-slate-700">Product or Service Focus</Label>
                <Input value={productFocus} onChange={(e) => setProductFocus(e.target.value)} placeholder="e.g. Cross-border asset settlements" className="mt-1" />
              </div>
              <div>
                <Label className="text-xs font-bold text-slate-700">Positive Keywords (comma-separated)</Label>
                <Input value={positiveKw} onChange={(e) => setPositiveKw(e.target.value)} placeholder="e.g. DeFi, RWA, treasury" className="mt-1" />
              </div>
              <div>
                <Label className="text-xs font-bold text-slate-700">Exclude Keywords (comma-separated)</Label>
                <Input value={excludeKw} onChange={(e) => setExcludeKw(e.target.value)} placeholder="e.g. crypto, airdrop" className="mt-1" />
              </div>
            </div>
          )}
          {step === 2 && (
            <div className="grid grid-cols-1 gap-4 max-w-lg">
              <div>
                <Label className="text-xs font-bold text-slate-700">Ideal Customer Profile (ICP) Industry</Label>
                <Input
                  data-testid="wizard-icp-industry"
                  value={icp.industry}
                  onChange={(e) => setIcp({ ...icp, industry: e.target.value })}
                  placeholder="e.g. Financial Institutions, Asset Management"
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs font-bold text-slate-700">Organization Type</Label>
                <Input value={icp.organization_type} onChange={(e) => setIcp({ ...icp, organization_type: e.target.value })} placeholder="e.g. Fund managers, commercial banks" className="mt-1" />
              </div>
              <div>
                <Label className="text-xs font-bold text-slate-700">Company Size Range</Label>
                <Input value={icp.company_size} onChange={(e) => setIcp({ ...icp, company_size: e.target.value })} placeholder="e.g. 50-200 employees" className="mt-1" />
              </div>
              <div>
                <Label className="text-xs font-bold text-slate-700">Target Roles & Titles (comma-separated)</Label>
                <Input
                  value={icp.role_or_title_targets.join(", ")}
                  onChange={(e) =>
                    setIcp({ ...icp, role_or_title_targets: splitCsv(e.target.value) })
                  }
                  placeholder="e.g. Head of RWA, VP Innovation, Portfolio Manager"
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs font-bold text-slate-700">Country or Region</Label>
                <Input value={icp.country_or_region} onChange={(e) => setIcp({ ...icp, country_or_region: e.target.value })} placeholder="e.g. Singapore, APAC" className="mt-1" />
              </div>
            </div>
          )}
          {step === 3 && (
            <div className="grid grid-cols-1 gap-4 max-w-lg">
              <div>
                <Label className="text-xs font-bold text-slate-700">Market Regions</Label>
                <Input value={regions} onChange={(e) => setRegions(e.target.value)} placeholder="e.g. US, EU, SG" className="mt-1" />
              </div>
              <div>
                <Label className="text-xs font-bold text-slate-700">Languages</Label>
                <Input value={languages} onChange={(e) => setLanguages(e.target.value)} placeholder="e.g. en, vi" className="mt-1" />
              </div>
              <div>
                <Label className="text-xs font-bold text-slate-700">Timezone</Label>
                <Input value={timezone} onChange={(e) => setTimezone(e.target.value)} placeholder="e.g. Asia/Singapore" className="mt-1" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs font-bold text-slate-700">Start Date</Label>
                  <Input type="date" value={dateStart} onChange={(e) => setDateStart(e.target.value)} className="mt-1" />
                </div>
                <div>
                  <Label className="text-xs font-bold text-slate-700">End Date</Label>
                  <Input type="date" value={dateEnd} onChange={(e) => setDateEnd(e.target.value)} className="mt-1" />
                </div>
              </div>
            </div>
          )}
          {step === 4 && (
            <div className="space-y-4" data-testid="wizard-sources">
              <p className="text-xs text-[var(--color-muted)]">
                Select from identified connectors. Disabled sources fail current governance policies.
              </p>
              {sources.length === 0 && <p className="text-xs text-slate-400 py-4">No sources registered. Add connectors in Admin.</p>}
              
              <div className="grid grid-cols-1 gap-2.5">
                {sources.map((s) => (
                  <label
                    key={s.id}
                    className={`flex items-start gap-3 border rounded-sm p-3 hover:bg-slate-50 transition-colors cursor-pointer ${
                      s.runnable ? "border-slate-200" : "opacity-50 border-slate-100 bg-slate-50/50 cursor-not-allowed"
                    }`}
                  >
                    <input
                      type="checkbox"
                      disabled={!s.runnable}
                      checked={selectedSourceIds.includes(s.id)}
                      onChange={(e) => {
                        if (e.target.checked) setSelectedSourceIds([...selectedSourceIds, s.id]);
                        else setSelectedSourceIds(selectedSourceIds.filter((id) => id !== s.id));
                      }}
                      className="mt-0.5 rounded-sm border-slate-300 text-slate-900 focus:ring-slate-900"
                    />
                    <div className="text-xs">
                      <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                        {s.name}
                        <span className="text-[9px] font-mono uppercase tracking-wider text-slate-400 bg-slate-100 px-1 rounded-sm">
                          {s.connector_type}
                        </span>
                      </div>
                      <p className="text-slate-500 mt-0.5 font-mono text-[10px]">{s.domain}</p>
                      {!s.runnable && (
                        <span className="block text-[10px] font-medium text-red-600 mt-1">Blocked: {s.denied_reasons.join(", ")}</span>
                      )}
                      {s.preferred_over_browser && s.runnable && (
                        <span className="block text-[10px] text-emerald-700 font-semibold mt-1">API Engine Preferred</span>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}
          {step === 5 && (
            <div className="space-y-4" data-testid="wizard-scoring-weights">
              <p className="text-xs text-[var(--color-muted)]">
                Configure weight percentages (0-1.00) mapping target priority matching values.
              </p>
              <div className="border border-slate-200 rounded-sm divide-y divide-slate-100">
                {Object.keys(DEFAULT_SCORING_WEIGHTS).map((key) => (
                  <div key={key} className="flex items-center justify-between p-3 gap-4 text-xs">
                    <Label className="font-medium text-slate-700">{SCORING_LABELS[key] ?? key}</Label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      max="1"
                      className="w-20 rounded-sm h-8 text-center font-mono font-bold"
                      value={weights[key]}
                      onChange={(e) => setWeights({ ...weights, [key]: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
          {step === 6 && (
            <div className="space-y-4" data-testid="wizard-review">
              <div className="border border-slate-200 bg-slate-50 p-4 rounded-sm text-xs space-y-2.5 max-w-lg">
                <div className="flex border-b border-slate-200 pb-1.5">
                  <span className="w-32 text-slate-500 font-mono">Campaign Name</span>
                  <span className="font-semibold text-slate-900">{name || "(not provided)"}</span>
                </div>
                <div className="flex border-b border-slate-200 pb-1.5">
                  <span className="w-32 text-slate-500 font-mono">Target Industry</span>
                  <span className="text-slate-800">{targetIndustry || "-"}</span>
                </div>
                <div className="flex border-b border-slate-200 pb-1.5">
                  <span className="w-32 text-slate-500 font-mono">ICP Industry</span>
                  <span className="text-slate-800">{icp.industry || "-"}</span>
                </div>
                <div className="flex pb-0.5">
                  <span className="w-32 text-slate-500 font-mono">Selected Sources</span>
                  <span className="font-mono text-slate-800 font-bold">{selectedSourceIds.length} sources</span>
                </div>
              </div>
              <p className="text-[11px] text-[var(--color-muted)] bg-slate-50 p-3 border border-slate-200 rounded-sm max-w-lg">
                Saving will create the campaign. You can trigger the discovery agent pipeline directly from the details page afterwards.
              </p>
            </div>
          )}
        </div>

        {/* Buttons / Actions */}
        <div className="mt-8 pt-5 border-t border-slate-100 flex gap-2 justify-end">
          <Link to="/campaigns" className="text-xs text-[var(--color-muted)] hover:text-slate-950 self-center mr-auto transition-colors">
            Cancel Creation
          </Link>
          
          {step > 0 && (
            <Button 
              type="button" 
              variant="ghost" 
              onClick={() => setStep(step - 1)}
              className="rounded-sm border border-slate-200 text-xs px-3.5 h-8.5 font-semibold text-slate-700 hover:bg-slate-50"
            >
              Back
            </Button>
          )}
          
          {step < STEPS.length - 1 ? (
            <Button 
              type="button" 
              onClick={() => setStep(step + 1)}
              className="rounded-sm text-xs px-3.5 h-8.5 font-semibold"
            >
              Next
            </Button>
          ) : (
            <Button 
              type="button" 
              data-testid="wizard-save" 
              disabled={!name.trim() || saving} 
              onClick={() => void save()}
              className="rounded-sm text-xs px-4 h-8.5 font-semibold"
            >
              {saving ? "Saving…" : "Save Campaign"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}