import type { Locale } from "@/i18n/routing";
import enMessages from "../../messages/en.json";
import zhTWMessages from "../../messages/zh-TW.json";

type NavItem = {
  label: string;
  href: string;
};

type FooterSection = {
  heading: string;
  items: Array<{ label: string; href: string }>;
};

type OptionItem = {
  value: string;
  label: string;
};

type Office = {
  city: string;
  address: string;
  phone: string;
  hours: string;
};

type LegalPageCopy = {
  metadata: {
    title: string;
    description: string;
  };
  breadcrumb: string;
  title: string;
  paragraphs?: string[];
  intro?: string;
  regions?: string[];
  regionTitle?: string;
  asideTitle?: string;
  asideDescription?: string;
};

type SiteCopy = {
  common: {
    home: string;
    faq: string;
    questions: string;
    localeFallbackTitle: string;
    localeFallbackDescription: string;
  };
  header: {
    nav: NavItem[];
    rfq: string;
    submitRfq: string;
    contact: string;
    openMenu: string;
    partnerTitle: string;
    partnerDescription: string;
  };
  footer: {
    sections: FooterSection[];
    description: string;
    certifications: string[];
    builtWithPrecision: string;
    allRightsReserved: string;
  };
  chat: {
    desktopButton: string;
    mobileButton: string;
    title: string;
    subtitle: string;
    suggestedQuestions: string;
    rfqReady: string;
    rfqReadyDescription: string;
    prepareRfq: string;
    thinking: string;
    placeholder: string;
    sendMessage: string;
    sessionUnavailable: string;
    requestFailed: string;
  };
  forms: {
    howOptions: OptionItem[];
    contact: {
      successTitle: string;
      successDescription: string;
      labels: {
        fullName: string;
        email: string;
        company: string;
        country: string;
        jobTitle: string;
        phone: string;
        message: string;
        howFound: string;
      };
      placeholders: {
        fullName: string;
        email: string;
        company: string;
        country: string;
        jobTitle: string;
        phone: string;
        message: string;
      };
      sending: string;
      submit: string;
      submitFailed: string;
      unexpectedError: string;
    };
    rfq: {
      howOptions: OptionItem[];
      timelineOptions: OptionItem[];
      successTitle: string;
      referenceNumber: string;
      successDescription: string;
      labels: {
        fullName: string;
        email: string;
        company: string;
        phone: string;
        country: string;
        jobTitle: string;
        quantity: string;
        specifications: string;
        timeline: string;
        message: string;
        howFound: string;
        consent: string;
      };
      placeholders: {
        quantity: string;
        specifications: string;
        message: string;
      };
      submitting: string;
      submit: string;
      footerNote: string;
      submitFailed: string;
      unexpectedError: string;
    };
  };
  contactPage: {
    metadata: {
      title: string;
      description: string;
    };
    breadcrumb: string;
    title: string;
    description: string;
    reasonsTitle: string;
    reasons: Array<{ label: string; desc: string }>;
    officesTitle: string;
    offices: Office[];
    responseTitle: string;
    responseDescription: string;
    formTitle: string;
    formDescription: string;
    quickLinksPrompt: string;
    quickLinks: {
      products: string;
      certifications: string;
      rfq: string;
    };
  };
  rfqPage: {
    metadata: {
      title: string;
      description: string;
    };
    title: string;
    description: string;
    builtForTitle: string;
    builtForItems: string[];
    helpTitle: string;
    helpDescription: string;
    helpCta: string;
    responseWindowLabel: string;
    responseWindowTime: string;
    responseWindowHours: string;
  };
  faqPage: {
    metadata: {
      title: string;
      description: string;
    };
    breadcrumb: string;
    title: string;
    description: string;
    emptyState: string;
    ctaTitle: string;
    ctaDescription: string;
    ctaButtons: {
      rfq: string;
      contact: string;
      applications: string;
    };
    allCategories: string;
  };
  docsPage: {
    metadata: {
      title: string;
      description: string;
    };
    breadcrumb: string;
    title: string;
    description: string;
    docs: Array<{ title: string; desc: string }>;
    noteTitle: string;
    noteDescription: string;
  };
  careersPage: {
    metadata: {
      title: string;
      description: string;
    };
    breadcrumb: string;
    title: string;
    description: string;
    rolesTitle: string;
    openings: string[];
    applyTitle: string;
    applyDescription: string;
  };
  newsPage: {
    metadata: {
      title: string;
      description: string;
    };
    breadcrumb: string;
    title: string;
    description: string;
    items: Array<{ date: string; title: string; summary: string }>;
  };
  legalPages: {
    privacy: LegalPageCopy;
    terms: LegalPageCopy;
    cookies: LegalPageCopy;
    dealers: LegalPageCopy;
  };
};

const MESSAGE_MAP = {
  en: enMessages,
  "zh-TW": zhTWMessages,
} as const;

type MessageBundle = typeof enMessages;

function buildHeaderNav(messages: MessageBundle): NavItem[] {
  return [
    { label: messages.header.nav.products, href: "/products" },
    { label: messages.header.nav.applications, href: "/applications" },
    { label: messages.header.nav.certifications, href: "/certifications" },
    { label: messages.header.nav.about, href: "/about" },
    { label: messages.header.nav.contact, href: "/contact" },
  ];
}

function buildFooterSections(messages: MessageBundle): FooterSection[] {
  return [
    {
      heading: messages.footer.sections.products.heading,
      items: [
        { label: messages.footer.sections.products.catalog, href: "/products" },
        { label: messages.footer.sections.products.applications, href: "/applications" },
        { label: messages.footer.sections.products.rfq, href: "/rfq" },
        { label: messages.footer.sections.products.custom, href: "/oem-odm" },
      ],
    },
    {
      heading: messages.footer.sections.company.heading,
      items: [
        { label: messages.footer.sections.company.about, href: "/about" },
        { label: messages.footer.sections.company.certifications, href: "/certifications" },
        { label: messages.footer.sections.company.news, href: "/news" },
        { label: messages.footer.sections.company.careers, href: "/careers" },
      ],
    },
    {
      heading: messages.footer.sections.support.heading,
      items: [
        { label: messages.footer.sections.support.faq, href: "/faq" },
        { label: messages.footer.sections.support.contact, href: "/contact" },
        { label: messages.footer.sections.support.docs, href: "/docs" },
        { label: messages.footer.sections.support.dealers, href: "/dealers" },
      ],
    },
    {
      heading: messages.footer.sections.legal.heading,
      items: [
        { label: messages.footer.sections.legal.privacy, href: "/privacy" },
        { label: messages.footer.sections.legal.terms, href: "/terms" },
        { label: messages.footer.sections.legal.cookies, href: "/cookies" },
      ],
    },
  ];
}

function toSiteCopy(messages: MessageBundle): SiteCopy {
  return {
    common: {
      home: messages.common.home,
      faq: messages.common.faq,
      questions: messages.common.questions,
      localeFallbackTitle: messages.common.localeFallbackTitle,
      localeFallbackDescription: messages.common.localeFallbackDescription,
    },
    header: {
      nav: buildHeaderNav(messages),
      rfq: messages.header.rfq,
      submitRfq: messages.header.submitRfq,
      contact: messages.header.contact,
      openMenu: messages.header.openMenu,
      partnerTitle: messages.header.partnerTitle,
      partnerDescription: messages.header.partnerDescription,
    },
    footer: {
      sections: buildFooterSections(messages),
      description: messages.footer.description,
      certifications: [...messages.footer.certifications],
      builtWithPrecision: messages.footer.builtWithPrecision,
      allRightsReserved: messages.footer.allRightsReserved,
    },
    chat: { ...messages.chat },
    forms: {
      howOptions: [...messages.forms.howOptions],
      contact: { ...messages.forms.contact },
      rfq: { ...messages.forms.rfq },
    },
    contactPage: { ...messages.contactPage },
    rfqPage: { ...messages.rfqPage },
    faqPage: { ...messages.faqPage },
    docsPage: { ...messages.docsPage },
    careersPage: { ...messages.careersPage },
    newsPage: { ...messages.newsPage },
    legalPages: {
      privacy: { ...messages.legal.privacy },
      terms: { ...messages.legal.terms },
      cookies: { ...messages.legal.cookies },
      dealers: { ...messages.legal.dealers },
    },
  };
}

export function resolveLocale(locale?: string): Locale {
  return locale?.toLowerCase() === "zh-tw" ? "zh-TW" : "en";
}

export function getSiteCopy(locale?: string): SiteCopy {
  return toSiteCopy(MESSAGE_MAP[resolveLocale(locale)]);
}
