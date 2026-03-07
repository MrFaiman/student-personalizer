import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import commonHe from "./locales/he/common.json";
import dashboardHe from "./locales/he/dashboard.json";
import studentsHe from "./locales/he/students.json";
import classesHe from "./locales/he/classes.json";
import uploadHe from "./locales/he/upload.json";
import teachersHe from "./locales/he/teachers.json";
import subjectsHe from "./locales/he/subjects.json";
import advancedAnalyticsHe from "./locales/he/advancedAnalytics.json";
import openDayHe from "./locales/he/open-day.json";

i18n.use(initReactI18next).init({
  lng: "he",
  fallbackLng: "he",
  defaultNS: "common",
  resources: {
    he: {
      common: commonHe,
      dashboard: dashboardHe,
      students: studentsHe,
      classes: classesHe,
      upload: uploadHe,
      teachers: teachersHe,
      subjects: subjectsHe,
      advancedAnalytics: advancedAnalyticsHe,
      openDay: openDayHe,
    },
  },
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
