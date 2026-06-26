import { adminApi } from './client';

export interface CatalogPagination {
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface CareerRow {
  id: string;
  title: string;
  category: string;
  level: string;
  description: string;
  requiredSkills: string[];
  salaryRange?: string;
  demandScore?: number;
  isActive?: boolean;
}

export interface CourseRow {
  id: string;
  title: string;
  provider: string;
  category: string;
  level: string;
  duration?: string;
  url?: string;
  skillsCovered: string[];
  isActive?: boolean;
}

export interface RoadmapRow {
  id: string;
  category: string;
  level: string;
  title: string;
  steps: string[];
  estimatedDuration?: string;
  isActive?: boolean;
}

export interface RuleRow {
  id: string;
  category: string;
  minimumScore: number;
  level: string;
  careers: string[];
  courses: string[];
  roadmapId?: string;
  priority?: number;
  isActive?: boolean;
}

export interface QuizTemplateRow {
  id: string;
  interest: string;
  level: string;
  totalQuestions: number;
  questions: unknown[];
}

const paginated = <T>(data: { data: T[]; pagination: CatalogPagination }) => ({
  items: data.data || [],
  pagination: data.pagination,
});

export const fetchCareers = async (params?: Record<string, string | number>) => {
  const { data } = await adminApi.get<{ success: boolean; data: CareerRow[]; pagination: CatalogPagination }>(
    '/catalog/careers',
    { params }
  );
  return paginated(data);
};

export const createCareer = async (payload: Partial<CareerRow>) => {
  const { data } = await adminApi.post('/catalog/careers', payload);
  return data.data as CareerRow;
};

export const updateCareer = async (id: string, payload: Partial<CareerRow>) => {
  const { data } = await adminApi.put(`/catalog/careers/${id}`, payload);
  return data.data as CareerRow;
};

export const deleteCareer = async (id: string) => {
  await adminApi.delete(`/catalog/careers/${id}`);
};

export const fetchCourses = async (params?: Record<string, string | number>) => {
  const { data } = await adminApi.get<{ success: boolean; data: CourseRow[]; pagination: CatalogPagination }>(
    '/catalog/courses',
    { params }
  );
  return paginated(data);
};

export const createCourse = async (payload: Partial<CourseRow>) => {
  const { data } = await adminApi.post('/catalog/courses', payload);
  return data.data as CourseRow;
};

export const updateCourse = async (id: string, payload: Partial<CourseRow>) => {
  const { data } = await adminApi.put(`/catalog/courses/${id}`, payload);
  return data.data as CourseRow;
};

export const deleteCourse = async (id: string) => {
  await adminApi.delete(`/catalog/courses/${id}`);
};

export const fetchRoadmaps = async (params?: Record<string, string | number>) => {
  const { data } = await adminApi.get<{ success: boolean; data: RoadmapRow[]; pagination: CatalogPagination }>(
    '/catalog/roadmaps',
    { params }
  );
  return paginated(data);
};

export const createRoadmap = async (payload: Partial<RoadmapRow>) => {
  const { data } = await adminApi.post('/catalog/roadmaps', payload);
  return data.data as RoadmapRow;
};

export const updateRoadmap = async (id: string, payload: Partial<RoadmapRow>) => {
  const { data } = await adminApi.put(`/catalog/roadmaps/${id}`, payload);
  return data.data as RoadmapRow;
};

export const deleteRoadmap = async (id: string) => {
  await adminApi.delete(`/catalog/roadmaps/${id}`);
};

export const fetchRules = async (params?: Record<string, string | number>) => {
  const { data } = await adminApi.get<{ success: boolean; data: RuleRow[]; pagination: CatalogPagination }>(
    '/catalog/recommendation-rules',
    { params }
  );
  return paginated(data);
};

export const createRule = async (payload: Partial<RuleRow>) => {
  const { data } = await adminApi.post('/catalog/recommendation-rules', payload);
  return data.data as RuleRow;
};

export const updateRule = async (id: string, payload: Partial<RuleRow>) => {
  const { data } = await adminApi.put(`/catalog/recommendation-rules/${id}`, payload);
  return data.data as RuleRow;
};

export const deleteRule = async (id: string) => {
  await adminApi.delete(`/catalog/recommendation-rules/${id}`);
};

export const fetchQuizBank = async (params?: Record<string, string | number>) => {
  const { data } = await adminApi.get<{ success: boolean; data: QuizTemplateRow[]; pagination: CatalogPagination }>(
    '/catalog/quiz-bank',
    { params }
  );
  return paginated(data);
};

export const seedCatalog = async (force = false) => {
  const { data } = await adminApi.post('/catalog/seed', { force });
  return data;
};

export const CATALOG_CATEGORIES = [
  'Coding',
  'Web Development',
  'Mobile Development',
  'AI & Machine Learning',
  'Data Science',
  'Cybersecurity',
  'Cloud Computing',
  'Game Development',
];

export const CATALOG_LEVELS = ['Beginner', 'Intermediate', 'Expert'] as const;
