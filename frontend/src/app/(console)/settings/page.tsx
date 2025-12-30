"use client";

import { useState } from "react";
import { SettingsLayout } from "@/components/settings/SettingsLayout";
import { ProfileSection } from "@/components/settings/ProfileSection";
import { ProvidersSection } from "@/components/settings/ProvidersSection";
import { ApiKeysSection } from "@/components/settings/ApiKeysSection";
import { SecuritySection } from "@/components/settings/SecuritySection";
import { BillingSection } from "@/components/settings/BillingSection";

/**
 * Page des paramètres refondue
 * Architecture modulaire avec navigation latérale
 */
export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("profile");

  const renderContent = () => {
    switch (activeTab) {
      case "profile":
        return <ProfileSection />;
      case "providers":
        return <ProvidersSection />;
      case "keys":
        return <ApiKeysSection />;
      case "security":
        return <SecuritySection />;
      case "billing":
        return <BillingSection />;
      default:
        return <ProfileSection />;
    }
  };

  return (
    <SettingsLayout activeTab={activeTab} onTabChange={setActiveTab}>
      {renderContent()}
    </SettingsLayout>
  );
}
