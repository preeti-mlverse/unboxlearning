// Short names for the generated API schemas. Type-only: nothing here exists at runtime.
import type { components } from "./api";

type S = components["schemas"];

export type Me = S["MeOut"];
export type Membership = S["MembershipOut"];
export type AuthResult = S["AuthOut"];
export type Organization = S["OrganizationOut"];
export type Member = S["MemberOut"];
export type CourseSummary = S["CourseSummary"];
export type CourseDetail = S["CourseDetail"];
export type Version = S["VersionOut"];
export type ModuleT = S["ModuleOut"];
export type LessonT = S["LessonOut"];
export type LessonDetail = S["LessonDetail"];
export type Block = S["BlockOut"];
export type DocumentT = S["DocumentOut"];
export type Job = S["JobOut"];
export type CatalogCourse = S["CatalogCourse"];
export type Enrollment = S["EnrollmentOut"];
export type LearnCourse = S["LearnCourseOut"];
export type LearnLesson = S["LearnLessonOut"];
export type LessonProgress = S["LessonProgressOut"];
export type AdminStats = S["AdminStats"];
export type AdminUser = S["AdminUserOut"];
export type AdminOrg = S["AdminOrgOut"];
export type SignupIn = S["SignupIn"];

export type CourseStatus = S["CourseStatus"];
export type VersionStatus = S["VersionStatus"];
export type DocumentStatus = S["DocumentStatus"];
export type JobStatus = S["JobStatus"];
export type ProgressStatus = S["ProgressStatus"];
export type OrgType = S["OrgType"];
export type Role = S["Role"];
export type Visibility = S["Visibility"];

/** Every error the API returns has this shape. */
export interface ApiErrorBody {
  error: { code: string; message: string; request_id?: string | null; details?: Record<string, unknown> };
}
