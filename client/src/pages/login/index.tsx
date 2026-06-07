// FORK: multi-tenancy — Landing / login page
import {
  ApiOutlined,
  GithubOutlined,
  GoogleOutlined,
  LockOutlined,
  ShareAltOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { Button, Card, Col, Divider, Row, Space, Spin, Typography, theme } from "antd";
import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useAuth } from "../../contexts/auth";
import { getAPIURL, getBasePath } from "../../utils/url";

const { Title, Text, Paragraph } = Typography;

const PROVIDER_ICONS: Record<string, React.ReactNode> = {
  google: <GoogleOutlined />,
  github: <GithubOutlined />,
};

const FEATURES = [
  {
    icon: <TeamOutlined style={{ fontSize: 28 }} />,
    title: "Multi-user",
    desc: "Each user has their own private inventory. Sign in with Google or GitHub — no passwords.",
  },
  {
    icon: <LockOutlined style={{ fontSize: 28 }} />,
    title: "Private by default",
    desc: "Your spools, filaments and vendors are visible only to you. Nothing shared unless you choose.",
  },
  {
    icon: <ShareAltOutlined style={{ fontSize: 28 }} />,
    title: "Share filament lists",
    desc: "Generate a public share link for your filament collection — great for sharing with your community.",
  },
  {
    icon: <ApiOutlined style={{ fontSize: 28 }} />,
    title: "API & MCP ready",
    desc: "Generate long-lived API tokens to connect scripts, automation tools, or AI agents via the built-in MCP server.",
  },
];

const ERROR_MESSAGES: Record<string, string> = {
  oauth_error: "Authentication failed. Please try again.",
  state_mismatch: "Security check failed. Please try again.",
  no_email: "Could not retrieve your email address. Please try a different provider.",
  domain_not_allowed: "Your email domain is not allowed. Contact your administrator.",
};

export default function LoginPage() {
  const { token } = theme.useToken();
  const { user, loading, providers, authEnabled } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const error = searchParams.get("error");

  useEffect(() => {
    if (!loading && user) navigate("/");
    if (!loading && !authEnabled) navigate("/");
  }, [user, loading, authEnabled, navigate]);

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
      <Spin size="large" />
    </div>
  );

  return (
    <div style={{ minHeight: "100vh", background: token.colorBgLayout }}>
      {/* Hero */}
      <div style={{
        textAlign: "center",
        padding: "64px 24px 48px",
        background: token.colorBgContainer,
        borderBottom: `1px solid ${token.colorBorderSecondary}`,
      }}>
        <img src={`${getBasePath()}/favicon.svg`} alt="Spoolman" style={{ width: 72, marginBottom: 20 }} />
        <Title style={{ marginBottom: 8 }}>Spoolman</Title>
        <Paragraph style={{ fontSize: 18, color: token.colorTextSecondary, maxWidth: 500, margin: "0 auto 32px" }}>
          Your personal 3D printing filament tracker — now with multi-user support, API access, and AI agent integration.
        </Paragraph>

        {/* Sign-in buttons */}
        <div style={{ maxWidth: 320, margin: "0 auto" }}>
          {error && (
            <Text type="danger" style={{ display: "block", marginBottom: 12 }}>
              {ERROR_MESSAGES[error] ?? "An error occurred. Please try again."}
            </Text>
          )}
          <Space direction="vertical" style={{ width: "100%" }}>
            {providers.map((provider) => (
              <Button
                key={provider.name}
                size="large"
                block
                icon={PROVIDER_ICONS[provider.name]}
                href={`${getAPIURL()}/auth/login/${provider.name}`}
                style={{ height: 48 }}
              >
                Continue with {provider.display_name}
              </Button>
            ))}
          </Space>
        </div>
      </div>

      {/* Feature grid */}
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "56px 24px 64px" }}>
        <Title level={3} style={{ textAlign: "center", marginBottom: 40, color: token.colorTextSecondary, fontWeight: 400 }}>
          What's included in this build
        </Title>
        <Row gutter={[24, 24]}>
          {FEATURES.map((f) => (
            <Col key={f.title} xs={24} sm={12}>
              <Card
                styles={{ body: { padding: "28px 24px" } }}
                style={{ height: "100%", borderColor: token.colorBorderSecondary }}
              >
                <div style={{ color: token.colorPrimary, marginBottom: 14 }}>{f.icon}</div>
                <Title level={5} style={{ marginBottom: 8 }}>{f.title}</Title>
                <Text type="secondary">{f.desc}</Text>
              </Card>
            </Col>
          ))}
        </Row>

        <Divider style={{ marginTop: 56 }} />
        <Text type="secondary" style={{ display: "block", textAlign: "center", fontSize: 13 }}>
          Based on{" "}
          <a href="https://github.com/Donkie/Spoolman" target="_blank" rel="noreferrer" style={{ color: token.colorTextSecondary }}>
            Spoolman
          </a>
          {" "}by Donkie — extended with multi-tenancy
        </Text>
      </div>
    </div>
  );
}
