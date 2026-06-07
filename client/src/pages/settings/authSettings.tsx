// FORK: multi-tenancy — API token and share link management
import { CopyOutlined, DeleteOutlined, LinkOutlined, PlusOutlined } from "@ant-design/icons";
import { Alert, Avatar, Button, Divider, Form, Input, List, Modal, Space, Tag, Typography, message } from "antd";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../contexts/auth";
import { getAPIURL, getBasePath } from "../../utils/url";

const { Text, Title } = Typography;

interface TokenInfo {
  id: number;
  name: string;
  created_at: string;
  last_used_at: string | null;
}

interface ShareLinkInfo {
  id: number;
  token: string;
  label: string | null;
  created_at: string;
}

function ApiTokens() {
  const [tokens, setTokens] = useState<TokenInfo[]>([]);
  const [creating, setCreating] = useState(false);
  const [newTokenValue, setNewTokenValue] = useState<string | null>(null);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    const r = await fetch(`${getAPIURL()}/auth/tokens`, { credentials: "include" });
    if (r.ok) setTokens(await r.json());
  }, []);

  useEffect(() => { load(); }, [load]);

  const onCreate = async (values: { name: string }) => {
    setCreating(true);
    try {
      const r = await fetch(`${getAPIURL()}/auth/tokens`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ name: values.name }),
      });
      const data = await r.json();
      setNewTokenValue(data.token);
      form.resetFields();
      load();
    } finally {
      setCreating(false);
    }
  };

  const onDelete = async (id: number) => {
    await fetch(`${getAPIURL()}/auth/tokens/${id}`, { method: "DELETE", credentials: "include" });
    load();
  };

  return (
    <div>
      <Title level={5}>API Tokens</Title>
      <Text type="secondary" style={{ display: "block", marginBottom: 12 }}>
        Long-lived tokens for programmatic access. Use as <code>Authorization: Bearer &lt;token&gt;</code>
      </Text>

      {newTokenValue && (
        <Alert
          type="success"
          showIcon
          message="Token created — copy it now, it won't be shown again"
          description={
            <Space>
              <code style={{ wordBreak: "break-all" }}>{newTokenValue}</code>
              <Button
                icon={<CopyOutlined />}
                size="small"
                onClick={() => { navigator.clipboard.writeText(newTokenValue); message.success("Copied!"); }}
              />
            </Space>
          }
          closable
          onClose={() => setNewTokenValue(null)}
          style={{ marginBottom: 12 }}
        />
      )}

      <Form form={form} layout="inline" onFinish={onCreate} style={{ marginBottom: 12 }}>
        <Form.Item name="name" rules={[{ required: true, message: "Token name required" }]}>
          <Input placeholder="Token name" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={creating} icon={<PlusOutlined />}>
            Generate
          </Button>
        </Form.Item>
      </Form>

      <List
        size="small"
        bordered
        dataSource={tokens}
        locale={{ emptyText: "No tokens yet" }}
        renderItem={(t) => (
          <List.Item
            actions={[
              <Button key="del" danger icon={<DeleteOutlined />} size="small" onClick={() => onDelete(t.id)} />,
            ]}
          >
            <List.Item.Meta
              title={t.name}
              description={`Created ${new Date(t.created_at).toLocaleDateString()}${t.last_used_at ? ` · Last used ${new Date(t.last_used_at).toLocaleDateString()}` : ""}`}
            />
          </List.Item>
        )}
      />
    </div>
  );
}

function ShareLinks() {
  const [links, setLinks] = useState<ShareLinkInfo[]>([]);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm();

  const load = useCallback(async () => {
    const r = await fetch(`${getAPIURL()}/auth/shares`, { credentials: "include" });
    if (r.ok) setLinks(await r.json());
  }, []);

  useEffect(() => { load(); }, [load]);

  const onCreate = async (values: { label?: string }) => {
    setCreating(true);
    try {
      await fetch(`${getAPIURL()}/auth/shares`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ label: values.label || null }),
      });
      form.resetFields();
      load();
    } finally {
      setCreating(false);
    }
  };

  const onDelete = async (id: number) => {
    await fetch(`${getAPIURL()}/auth/shares/${id}`, { method: "DELETE", credentials: "include" });
    load();
  };

  const shareUrl = (token: string) => `${window.location.origin}${getBasePath()}/share/${token}`;

  return (
    <div>
      <Title level={5}>Filament Share Links</Title>
      <Text type="secondary" style={{ display: "block", marginBottom: 12 }}>
        Public links to share your filament list. Anyone with the link can view it without logging in.
      </Text>

      <Form form={form} layout="inline" onFinish={onCreate} style={{ marginBottom: 12 }}>
        <Form.Item name="label">
          <Input placeholder="Label (optional)" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={creating} icon={<LinkOutlined />}>
            Create Share Link
          </Button>
        </Form.Item>
      </Form>

      <List
        size="small"
        bordered
        dataSource={links}
        locale={{ emptyText: "No share links yet" }}
        renderItem={(l) => (
          <List.Item
            actions={[
              <Button
                key="copy"
                icon={<CopyOutlined />}
                size="small"
                onClick={() => { navigator.clipboard.writeText(shareUrl(l.token)); message.success("Copied!"); }}
              />,
              <Button key="del" danger icon={<DeleteOutlined />} size="small" onClick={() => onDelete(l.id)} />,
            ]}
          >
            <List.Item.Meta
              title={l.label ?? <Text type="secondary">Unlabeled</Text>}
              description={shareUrl(l.token)}
            />
          </List.Item>
        )}
      />
    </div>
  );
}

export const AuthSettings = () => {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <div>
      <Title level={4}>Account</Title>

      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
        {user.avatar_url && <Avatar src={user.avatar_url} size={48} />}
        <div>
          <div style={{ fontWeight: 500, fontSize: 16 }}>{user.name}</div>
          <Tag>{user.email}</Tag>
        </div>
        <Button onClick={logout} style={{ marginLeft: "auto" }}>Sign out</Button>
      </div>

      <Divider />
      <ApiTokens />
      <Divider />
      <ShareLinks />
    </div>
  );
};
