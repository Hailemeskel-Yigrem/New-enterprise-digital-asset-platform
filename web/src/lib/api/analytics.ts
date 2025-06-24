import { apiClient } from "@/lib/api/client";
import type {
  ActivityFeedResponse,
  DashboardResponse,
  ReportDimension,
  UsageReportResponse,
} from "@/lib/types";

export async function getDashboard(): Promise<DashboardResponse> {
  return apiClient<DashboardResponse>("/analytics/dashboard");
}

export async function getActivityFeed(params: {
  limit?: number;
  offset?: number;
} = {}): Promise<ActivityFeedResponse> {
  return apiClient<ActivityFeedResponse>("/activity/feed", {
    method: "POST",
    body: params,
  });
}

export async function getUsageReport(dimension: ReportDimension): Promise<UsageReportResponse> {
  return apiClient<UsageReportResponse>("/reports/usage", {
    method: "POST",
    body: { dimension },
  });
}
