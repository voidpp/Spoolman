import { Show } from "@refinedev/antd";
import { useShow, useTranslate } from "@refinedev/core";
import { Button, Card, Col, Descriptions, Row, Space, Tag, Typography, theme } from "antd";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { useNavigate } from "react-router";
import { ExtraFieldDisplay } from "../../components/extraFields";
import { NumberFieldUnit } from "../../components/numberField";
import SpoolIcon from "../../components/spoolIcon";
import { enrichText } from "../../utils/parsing";
import { EntityType, useGetFields } from "../../utils/queryFields";
import { useCurrencyFormatter } from "../../utils/settings";
import { IFilament } from "./model";

dayjs.extend(utc);

const { Title, Text, Link } = Typography;

const fmtDate = (val: string | undefined) => {
  if (!val) return "—";
  return dayjs.utc(val).local().format("YYYY-MM-DD HH:mm");
};

export const FilamentShow = () => {
  const t = useTranslate();
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const extraFields = useGetFields(EntityType.filament);
  const currencyFormatter = useCurrencyFormatter();

  const { query } = useShow<IFilament>({ liveMode: "auto" });
  const { data, isLoading } = query;
  const record = data?.data;

  const formatTitle = (item: IFilament) => {
    const vendorPrefix = item.vendor ? `${item.vendor.name} - ` : "";
    return t("filament.titles.show_title", {
      id: item.id,
      name: vendorPrefix + item.name,
      interpolation: { escapeValue: false },
    });
  };

  const colorObj = record?.multi_color_hexes
    ? {
        colors: record.multi_color_hexes.split(","),
        vertical: record.multi_color_direction === "longitudinal",
      }
    : record?.color_hex;

  return (
    <Show
      isLoading={isLoading}
      title={record ? formatTitle(record) : ""}
      headerButtons={({ defaultButtons }) => (
        <>
          <Button
            type="primary"
            onClick={() => navigate(`/spool#filters=[{"field":"filament.id","operator":"in","value":[${record?.id}]}]`)}
          >
            {t("filament.fields.spools")}
          </Button>
          {defaultButtons}
        </>
      )}
    >
      {/* ── Hero ── */}
      <Card style={{ marginBottom: 24, borderColor: token.colorBorderSecondary }}>
        <Row gutter={32} align="middle" wrap>
          {/* Color swatch / spool icon — only when color is actually set */}
          {colorObj && (
            <Col flex="none">
              <SpoolIcon color={colorObj} size="large" no_margin />
            </Col>
          )}

          {/* Filament identity */}
          <Col flex="auto">
            <Space direction="vertical" size={4}>
              {record?.vendor ? (
                <Link
                  onClick={() => navigate(`/vendor/show/${record.vendor?.id}`)}
                  style={{ fontSize: 13, cursor: "pointer" }}
                >
                  {record.vendor.name}
                </Link>
              ) : null}
              <Title level={3} style={{ margin: 0 }}>
                {record?.name ?? `Filament #${record?.id}`}
              </Title>
              <Space size={8} wrap>
                {record?.material && <Tag color="blue">{record.material}</Tag>}
                {record?.color_hex && (
                  <Tag
                    style={{
                      background: `#${record.color_hex}`,
                      border: "1px solid rgba(128,128,128,0.3)",
                      color: parseInt(record.color_hex, 16) > 0x7fffff ? "#000" : "#fff",
                    }}
                  >
                    #{record.color_hex}
                  </Tag>
                )}
                {record?.diameter && <Tag>⌀ {record.diameter} mm</Tag>}
              </Space>
            </Space>
          </Col>

          {/* Price */}
          {record?.price != null && (
            <Col flex="none">
              <Space direction="vertical" size={2} style={{ textAlign: "right" }}>
                <Text type="secondary" style={{ fontSize: 12 }}>{t("filament.fields.price")}</Text>
                <Text strong style={{ fontSize: 20 }}>{currencyFormatter.format(record.price)}</Text>
              </Space>
            </Col>
          )}
        </Row>
      </Card>

      {/* ── Details grid ── */}
      <Row gutter={[16, 16]}>
        {/* Physical specs */}
        <Col xs={24} lg={12}>
          <Card title={t("filament.titles.specs", "Specifications")} size="small" style={{ height: "100%" }}>
            <Descriptions column={1} size="small" styles={{ label: { width: 160 } }}>
              <Descriptions.Item label={t("filament.fields.density")}>
                <NumberFieldUnit value={record?.density ?? ""} unit="g/cm³" options={{ maximumFractionDigits: 2, minimumFractionDigits: 2 }} />
              </Descriptions.Item>
              <Descriptions.Item label={t("filament.fields.diameter")}>
                <NumberFieldUnit value={record?.diameter ?? ""} unit="mm" options={{ maximumFractionDigits: 2, minimumFractionDigits: 2 }} />
              </Descriptions.Item>
              {record?.weight != null && (
                <Descriptions.Item label={t("filament.fields.weight")}>
                  <NumberFieldUnit value={record.weight} unit="g" options={{ maximumFractionDigits: 1, minimumFractionDigits: 1 }} />
                </Descriptions.Item>
              )}
              {record?.spool_weight != null && (
                <Descriptions.Item label={t("filament.fields.spool_weight")}>
                  <NumberFieldUnit value={record.spool_weight} unit="g" options={{ maximumFractionDigits: 1, minimumFractionDigits: 1 }} />
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        </Col>

        {/* Print settings */}
        <Col xs={24} lg={12}>
          <Card title={t("filament.titles.print_settings", "Print Settings")} size="small" style={{ height: "100%" }}>
            <Descriptions column={1} size="small" styles={{ label: { width: 160 } }}>
              <Descriptions.Item label={t("filament.fields.settings_extruder_temp")}>
                {record?.settings_extruder_temp != null
                  ? <NumberFieldUnit value={record.settings_extruder_temp} unit="°C" />
                  : <Text type="secondary">—</Text>}
              </Descriptions.Item>
              <Descriptions.Item label={t("filament.fields.settings_bed_temp")}>
                {record?.settings_bed_temp != null
                  ? <NumberFieldUnit value={record.settings_bed_temp} unit="°C" />
                  : <Text type="secondary">—</Text>}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        {/* Details */}
        <Col xs={24}>
          <Card title={t("filament.titles.details", "Details")} size="small">
            <Descriptions column={{ xs: 1, sm: 2 }} size="small" styles={{ label: { width: 160 } }}>
              <Descriptions.Item label={t("filament.fields.id")}>#{record?.id}</Descriptions.Item>
              <Descriptions.Item label={t("filament.fields.registered")}>{fmtDate(record?.registered)}</Descriptions.Item>
              {record?.price != null && (
                <Descriptions.Item label={t("filament.fields.price")}>{currencyFormatter.format(record.price)}</Descriptions.Item>
              )}
              {record?.vendor && (
                <Descriptions.Item label={t("filament.fields.vendor")}>
                  <Link onClick={() => navigate(`/vendor/show/${record.vendor?.id}`)} style={{ cursor: "pointer" }}>
                    {record.vendor.name}
                  </Link>
                </Descriptions.Item>
              )}
              {record?.article_number && (
                <Descriptions.Item label={t("filament.fields.article_number")}>{record.article_number}</Descriptions.Item>
              )}
              {record?.external_id && (
                <Descriptions.Item label={t("filament.fields.external_id")}>{record.external_id}</Descriptions.Item>
              )}
              {record?.comment && (
                <Descriptions.Item label={t("filament.fields.comment")} span={2}>
                  {enrichText(record.comment)}
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        </Col>

        {/* Extra fields */}
        {extraFields?.data && extraFields.data.length > 0 && (
          <Col xs={24}>
            <Card title={t("settings.extra_fields.tab")} size="small">
              <Descriptions column={{ xs: 1, sm: 2 }} size="small" styles={{ label: { width: 160 } }}>
                {extraFields.data.map((field, index) => (
                  <Descriptions.Item key={index} label={field.name}>
                    <ExtraFieldDisplay field={field} value={record?.extra[field.key]} />
                  </Descriptions.Item>
                ))}
              </Descriptions>
            </Card>
          </Col>
        )}
      </Row>
    </Show>
  );
};

export default FilamentShow;
