import { NavLink } from "react-router-dom";


const navigationItems = [
  { to: "/", label: "Главная" },
  { to: "/products/new", label: "Добавить товар" },
];


export function Header() {
  return (
    <header className="app-header">
      <div className="app-shell app-header__inner">
        <div>
          <p className="app-header__eyebrow">Reviews Platform</p>
          <span className="app-header__title">Frontend Service</span>
        </div>
        <nav className="app-nav">
          {navigationItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `app-nav__link${isActive ? " app-nav__link--active" : ""}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
