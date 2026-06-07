import { DownOutlined, LogoutOutlined, UserOutlined } from "@ant-design/icons";
import type { RefineThemedLayoutHeaderProps } from "@refinedev/antd";
import { useGetLocale, useSetLocale } from "@refinedev/core";
import { Avatar, Layout as AntdLayout, Button, Dropdown, MenuProps, Space, Switch, Tooltip, theme } from "antd";
import React, { useContext } from "react";
import { ColorModeContext } from "../../contexts/color-mode";
import { useAuth } from "../../contexts/auth"; // FORK: multi-tenancy

import { languages } from "../../i18n";
import QRCodeScannerModal from "../qrCodeScanner";

const { useToken } = theme;

export const Header = ({ sticky }: RefineThemedLayoutHeaderProps) => {
  const { token } = useToken();
  const locale = useGetLocale();
  const changeLanguage = useSetLocale();
  const { mode, setMode } = useContext(ColorModeContext);
  const { user, authEnabled } = useAuth(); // FORK: multi-tenancy

  const currentLocale = locale();

  const menuItems: MenuProps["items"] = [...(Object.keys(languages) || [])].sort().map((lang: string) => ({
    key: lang,
    onClick: () => changeLanguage(lang),
    label: languages[lang].name,
  }));

  const headerStyles: React.CSSProperties = {
    backgroundColor: token.colorBgElevated,
    display: "flex",
    justifyContent: "flex-end",
    alignItems: "center",
    padding: "0px 24px",
    height: "64px",
  };

  if (sticky) {
    headerStyles.position = "sticky";
    headerStyles.top = 0;
    headerStyles.zIndex = 1;
  }

  return (
    <AntdLayout.Header style={headerStyles}>
      <Space>
        <Dropdown
          menu={{
            items: menuItems,
            selectedKeys: currentLocale ? [currentLocale] : [],
          }}
        >
          <Button type="text">
            <Space>
              {languages[currentLocale ?? "en"].name}
              <DownOutlined />
            </Space>
          </Button>
        </Dropdown>
        <Switch
          checkedChildren="🌛"
          unCheckedChildren="🔆"
          onChange={() => setMode(mode === "light" ? "dark" : "light")}
          defaultChecked={mode === "dark"}
        />
        <QRCodeScannerModal />
        {/* FORK: multi-tenancy — user avatar + logout */}
        {authEnabled && user && (
          <Space style={{ cursor: "default", marginLeft: 8 }}>
            <Tooltip title={`${user.name} (${user.email})`}>
              <Space>
                {user.avatar_url ? (
                  <Avatar src={user.avatar_url} size={32} />
                ) : (
                  <Avatar size={32} icon={<UserOutlined />} style={{ backgroundColor: token.colorPrimary }} />
                )}
                <span style={{ fontSize: 14, maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {user.name}
                </span>
              </Space>
            </Tooltip>
            <Tooltip title="Sign out">
              <Button
                type="text"
                size="small"
                icon={<LogoutOutlined />}
                onClick={async () => {
                  await fetch("/api/v1/auth/logout", { method: "POST" });
                  window.location.href = "/login";
                }}
              />
            </Tooltip>
          </Space>
        )}
      </Space>
    </AntdLayout.Header>
  );
};
