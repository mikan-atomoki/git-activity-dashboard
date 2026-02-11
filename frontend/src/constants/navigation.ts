export interface NavItem {
  label: string;
  href: string;
  icon: string;
}

export const NAV_ITEMS: NavItem[] = [
  {
    label: "Dashboard",
    href: "/",
    icon: "\u{1F4CA}", // chart emoji
  },
  {
    label: "Trends",
    href: "/trends",
    icon: "\u{1F4C8}", // trending up emoji
  },
  {
    label: "Settings",
    href: "/settings",
    icon: "\u2699\uFE0F", // gear emoji
  },
];
