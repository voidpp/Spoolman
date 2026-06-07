// FORK: multi-tenancy — Public share page
import { HighlightOutlined } from "@ant-design/icons";
import { Card, List, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { useParams } from "react-router";
import { getAPIURL } from "../../utils/url";

const { Title, Text } = Typography;

interface Filament {
  id: number;
  name?: string;
  material?: string;
  color_hex?: string;
  vendor?: { name: string };
  weight?: number;
  diameter?: number;
}

interface ShareData {
  label: string | null;
  filaments: Filament[];
}

export default function SharePage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<ShareData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    fetch(`${getAPIURL()}/auth/share/${token}`)
      .then((r) => {
        if (!r.ok) throw new Error("Share link not found or expired.");
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message));
  }, [token]);

  if (error) {
    return (
      <div style={{ padding: 32, textAlign: "center" }}>
        <Text type="danger">{error}</Text>
      </div>
    );
  }

  if (!data) {
    return <div style={{ padding: 32, textAlign: "center" }}>Loading…</div>;
  }

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: 24 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
        <HighlightOutlined style={{ fontSize: 28 }} />
        <Title level={3} style={{ margin: 0 }}>
          {data.label ?? "Shared Filaments"}
        </Title>
      </div>
      <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
        {data.filaments.length} filament{data.filaments.length !== 1 ? "s" : ""}
      </Text>

      <List
        grid={{ gutter: 16, column: 2 }}
        dataSource={data.filaments}
        renderItem={(f) => (
          <List.Item>
            <Card size="small">
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {f.color_hex && (
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: "50%",
                      background: `#${f.color_hex}`,
                      border: "1px solid rgba(0,0,0,0.1)",
                      flexShrink: 0,
                    }}
                  />
                )}
                <div>
                  <div style={{ fontWeight: 500 }}>{f.name ?? "Unnamed"}</div>
                  <div style={{ fontSize: 12, color: "#888" }}>
                    {f.vendor?.name && <span>{f.vendor.name} · </span>}
                    {f.material && <Tag>{f.material}</Tag>}
                    {f.weight && <span>{f.weight}g</span>}
                  </div>
                </div>
              </div>
            </Card>
          </List.Item>
        )}
      />
    </div>
  );
}
