// Простые линейные иконки в стиле меню Альфа-Бизнеса.
import type { SVGProps } from 'react';

type P = SVGProps<SVGSVGElement>;
const base = { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.7, strokeLinecap: 'round', strokeLinejoin: 'round' } as const;

export const IconGrid = (p: P) => (<svg {...base} {...p}><circle cx="7" cy="7" r="2.5" /><circle cx="17" cy="7" r="2.5" /><circle cx="7" cy="17" r="2.5" /><path d="M17 14v6M14 17h6" /></svg>);
export const IconDoc = (p: P) => (<svg {...base} {...p}><path d="M6 3h9l4 4v14H6z" /><path d="M9 12h7M9 16h5" /></svg>);
export const IconPlus = (p: P) => (<svg {...base} {...p}><path d="M12 5v14M5 12h14" /></svg>);
export const IconInbox = (p: P) => (<svg {...base} {...p}><path d="M4 13l2-8h12l2 8v6H4z" /><path d="M4 13h5l1 2h4l1-2h5" /></svg>);
export const IconClock = (p: P) => (<svg {...base} {...p}><circle cx="12" cy="12" r="8" /><path d="M12 8v4l3 2" /></svg>);
export const IconUpload = (p: P) => (<svg {...base} {...p}><path d="M6 3h9l4 4v14H6z" /><path d="M12 17v-6M9.5 13.5L12 11l2.5 2.5" /></svg>);
export const IconList = (p: P) => (<svg {...base} {...p}><rect x="5" y="4" width="14" height="16" rx="2" /><path d="M9 9h6M9 13h6" /></svg>);
export const IconUsers = (p: P) => (<svg {...base} {...p}><circle cx="9" cy="8" r="3" /><path d="M3.5 19c.6-3 2.8-5 5.5-5s4.9 2 5.5 5" /><path d="M15.5 5.5a3 3 0 010 5.5M17.5 14c1.6.6 2.7 2.4 3 5" /></svg>);
export const IconCard = (p: P) => (<svg {...base} {...p}><rect x="3" y="6" width="18" height="13" rx="2" /><path d="M3 10h18" /></svg>);
export const IconGov = (p: P) => (<svg {...base} {...p}><path d="M4 10l8-5 8 5" /><path d="M6 10v8M10 10v8M14 10v8M18 10v8M4 20h16" /></svg>);
export const IconSettings = (p: P) => (<svg {...base} {...p}><circle cx="12" cy="12" r="3" /><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M5.6 18.4l1.8-1.8M16.6 7.4l1.8-1.8" /></svg>);
export const IconSpark = (p: P) => (<svg {...base} {...p}><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" /><path d="M19 16l.7 1.8 1.8.7-1.8.7L19 21l-.7-1.8-1.8-.7 1.8-.7z" /></svg>);
export const IconMail = (p: P) => (<svg {...base} {...p}><rect x="3" y="5" width="18" height="14" rx="2" /><path d="M3 7l9 6 9-6" /></svg>);
export const IconBell = (p: P) => (<svg {...base} {...p}><path d="M6 16V11a6 6 0 1112 0v5l1.5 2h-15z" /><path d="M10 20a2 2 0 004 0" /></svg>);
export const IconChevron = (p: P) => (<svg {...base} {...p}><path d="M9 6l6 6-6 6" /></svg>);
export const IconChevronDown = (p: P) => (<svg {...base} {...p}><path d="M6 9l6 6 6-6" /></svg>);
export const IconClose = (p: P) => (<svg {...base} {...p}><path d="M6 6l12 12M18 6L6 18" /></svg>);
export const IconSend = (p: P) => (<svg {...base} {...p}><path d="M4 12l16-8-6 16-2-7z" /></svg>);
export const IconRoute = (p: P) => (<svg {...base} {...p}><circle cx="6" cy="6" r="2.5" /><circle cx="18" cy="18" r="2.5" /><path d="M8.5 6H15a3 3 0 010 6H9a3 3 0 000 6h6.5" /></svg>);
export const IconChat = (p: P) => (<svg {...base} {...p}><path d="M4 5h16v11H9l-5 4z" /></svg>);
export const IconLink = (p: P) => (<svg {...base} {...p}><path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1" /><path d="M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1" /></svg>);
export const IconBank = (p: P) => (<svg {...base} {...p}><path d="M12 3l9 5H3z" /><path d="M5 10v7M9.5 10v7M14.5 10v7M19 10v7M3 20h18" /></svg>);
export const IconCheck = (p: P) => (<svg {...base} {...p}><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>);
export const IconEye = (p: P) => (<svg {...base} {...p}><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" /><circle cx="12" cy="12" r="2.8" /></svg>);
