import { InboxOutlined, PrinterOutlined, ToTopOutlined, ToolOutlined } from "@ant-design/icons";
import { Show } from "@refinedev/antd";
import { useInvalidate, useShow, useTranslate } from "@refinedev/core";
import { Button, Card, Col, Descriptions, Modal, Progress, Row, Space, Tag, Typography, theme } from "antd";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { ExtraFieldDisplay } from "../../components/extraFields";
import { NumberFieldUnit } from "../../components/numberField";
import SpoolIcon from "../../components/spoolIcon";
import { enrichText } from "../../utils/parsing";
import { EntityType, useGetFields } from "../../utils/queryFields";
import { useCurrencyFormatter } from "../../utils/settings";
import { getBasePath } from "../../utils/url";
import { IFilament } from "../filaments/model";
import { setSpoolArchived, useSpoolAdjustModal } from "./functions";
import { ISpool } from "./model";

dayjs.extend(utc);

const { Title, Text } = Typography;
const { confirm } = Modal;

const fmtDate = (val: string | undefined, includeTime = false) => {
  if (!val) return null;
  return dayjs.utc(val).local().format(includeTime ? "YYYY-MM-DD HH:mm" : "YYYY-MM-DD");
};

export const SpoolShow = () => {
  const t = useTranslate();
  const { token } = theme.useToken();
  const extraFields = useGetFields(EntityType.spool);
  const currencyFormatter = useCurrencyFormatter();
  const invalidate = useInvalidate();

  const { query } = useShow<ISpool>({ liveMode: "auto" });
  const { data, isLoading } = query;
  const record = data?.data;

  const spoolPrice = (item?: ISpool) => {
    const price = item?.price ?? item?.filament.price;
    return price !== undefined ? currencyFormatter.format(price) : null;
  };

  const { openSpoolAdjustModal, spoolAdjustModal } = useSpoolAdjustModal();

  const archiveSpool = async (spool: ISpool, archive: boolean) => {
    await setSpoolArchived(spool, archive);
    invalidate({ resource: "spool", id: spool.id, invalidates: ["list", "detail"] });
  };

  const archiveSpoolPopup = async (spool: ISpool | undefined) => {
    if (!spool) return;
    if (spool.remaining_weight != undefined && spool.remaining_weight <= 0) {
      await archiveSpool(spool, true);
    } else {
      confirm({
        title: t("spool.titles.archive"),
        content: t("spool.messages.archive"),
        okText: t("buttons.archive"),
        okType: "primary",
        cancelText: t("buttons.cancel"),
        onOk() { return archiveSpool(spool, true); },
      });
    }
  };

  const formatFilament = (item: IFilament) => {
    const vendor = item.vendor ? `${item.vendor.name} — ` : "";
    const name = item.name ?? `ID: ${item.id}`;
    return `${vendor}${name}`;
  };

  const formatTitle = (item: ISpool) =>
    t("spool.titles.show_title", {
      id: item.id,
      name: formatFilament(item.filament),
      interpolation: { escapeValue: false },
    });

  const colorObj = record?.filament.multi_color_hexes
    ? {
        colors: record.filament.multi_color_hexes.split(","),
        vertical: record.filament.multi_color_direction === "longitudinal",
      }
    : record?.filament.color_hex;

  // Remaining weight as percentage of initial weight
  const remainPct =
    record?.remaining_weight != null && record?.initial_weight
      ? Math.round((record.remaining_weight / record.initial_weight) * 100)
      : null;

  const remainColor =
    remainPct == null ? token.colorPrimary :
    remainPct > 40 ? token.colorSuccess :
    remainPct > 15 ? token.colorWarning :
    token.colorError;

  return (
    <Show
      isLoading={isLoading}
      title={record ? formatTitle(record) : ""}
      headerButtons={({ defaultButtons }) => (
        <>
          <Button type="primary" icon={<ToolOutlined />} onClick={() => record && openSpoolAdjustModal(record)}>
            {t("spool.titles.adjust")}
          </Button>
          <Button
            type="primary"
            icon={<PrinterOutlined />}
            href={getBasePath() + "/spool/print?spools=" + record?.id + "&return=" + encodeURIComponent(window.location.pathname)}
          >
            {t("printing.qrcode.button")}
          </Button>
          {record?.archived ? (
            <Button icon={<ToTopOutlined />} onClick={() => archiveSpool(record, false)}>
              {t("buttons.unArchive")}
            </Button>
          ) : (
            <Button danger icon={<InboxOutlined />} onClick={() => archiveSpoolPopup(record)}>
              {t("buttons.archive")}
            </Button>
          )}
          {defaultButtons}
          {spoolAdjustModal}
        </>
      )}
    >
      {/* ── Hero ── */}
      <Card style={{ marginBottom: 24, borderColor: token.colorBorderSecondary }}>
        <Row gutter={32} align="middle" wrap>
          {/* Spool icon — only when color is actually set */}
          {colorObj && (
            <Col flex="none">
              <SpoolIcon color={colorObj} size="large" no_margin />
            </Col>
          )}

          {/* Filament info */}
          <Col flex="auto">
            <Space direction="vertical" size={4} style={{ width: "100%" }}>
              {record?.filament.vendor && (
                <Text type="secondary" style={{ fontSize: 13 }}>{record.filament.vendor.name}</Text>
              )}
              <Title level={3} style={{ margin: 0 }}>
                {record?.filament.name ?? `Filament #${record?.filament.id}`}
              </Title>
              <Space size={8} wrap>
                {record?.filament.material && <Tag color="blue">{record.filament.material}</Tag>}
                {record?.archived && <Tag color="default">{t("buttons.archive")}</Tag>}
                {record?.location && <Tag icon={null}>📍 {record.location}</Tag>}
              </Space>
            </Space>
          </Col>

          {/* Remaining weight */}
          {record?.remaining_weight != null && (
            <Col flex="200px" style={{ minWidth: 160 }}>
              <Space direction="vertical" size={4} style={{ width: "100%" }}>
                <Text type="secondary" style={{ fontSize: 12 }}>{t("spool.fields.remaining_weight")}</Text>
                <Text strong style={{ fontSize: 22, color: remainColor }}>
                  <NumberFieldUnit
                    value={record.remaining_weight}
                    unit="g"
                    options={{ maximumFractionDigits: 0 }}
                  />
                </Text>
                {remainPct != null && (
                  <Progress
                    percent={remainPct}
                    strokeColor={remainColor}
                    showInfo={true}
                    size="small"
                    style={{ marginBottom: 0 }}
                  />
                )}
              </Space>
            </Col>
          )}
        </Row>
      </Card>

      {/* ── Details grid ── */}
      <Row gutter={[16, 16]}>
        {/* Stock */}
        <Col xs={24} lg={12}>
          <Card
            title={t("spool.titles.weight_usage", "Weight & Usage")}
            size="small"
            style={{ height: "100%" }}
          >
            <Descriptions column={1} size="small" styles={{ label: { width: 160 } }}>
              <Descriptions.Item label={t("spool.fields.remaining_weight")}>
                {record?.remaining_weight != null
                  ? <NumberFieldUnit value={record.remaining_weight} unit="g" options={{ maximumFractionDigits: 1 }} />
                  : "—"}
              </Descriptions.Item>
              <Descriptions.Item label={t("spool.fields.used_weight")}>
                {record?.used_weight != null
                  ? <NumberFieldUnit value={record.used_weight} unit="g" options={{ maximumFractionDigits: 1 }} />
                  : "—"}
              </Descriptions.Item>
              <Descriptions.Item label={t("spool.fields.remaining_length")}>
                {record?.remaining_length != null
                  ? <NumberFieldUnit value={record.remaining_length} unit="mm" options={{ maximumFractionDigits: 0 }} />
                  : "—"}
              </Descriptions.Item>
              <Descriptions.Item label={t("spool.fields.used_length")}>
                {record?.used_length != null
                  ? <NumberFieldUnit value={record.used_length} unit="mm" options={{ maximumFractionDigits: 0 }} />
                  : "—"}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        {/* Dates */}
        <Col xs={24} lg={12}>
          <Card title={t("spool.titles.dates", "Dates")} size="small" style={{ height: "100%" }}>
            <Descriptions column={1} size="small" styles={{ label: { width: 160 } }}>
              <Descriptions.Item label={t("spool.fields.registered")}>
                {fmtDate(record?.registered, true) ?? "—"}
              </Descriptions.Item>
              {record?.purchased && (
                <Descriptions.Item label={t("spool.fields.purchased")}>
                  {fmtDate(record.purchased)}
                </Descriptions.Item>
              )}
              {record?.first_used && (
                <Descriptions.Item label={t("spool.fields.first_used")}>
                  {fmtDate(record.first_used, true)}
                </Descriptions.Item>
              )}
              {record?.last_used && (
                <Descriptions.Item label={t("spool.fields.last_used")}>
                  {fmtDate(record.last_used, true)}
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        </Col>

        {/* Details */}
        <Col xs={24}>
          <Card title={t("spool.titles.details", "Details")} size="small">
            <Descriptions column={{ xs: 1, sm: 2 }} size="small" styles={{ label: { width: 140 } }}>
              {spoolPrice(record) && (
                <Descriptions.Item label={t("spool.fields.price")}>
                  {spoolPrice(record)}
                </Descriptions.Item>
              )}
              <Descriptions.Item label={t("spool.fields.id")}>
                #{record?.id}
              </Descriptions.Item>
              {record?.lot_nr && (
                <Descriptions.Item label={t("spool.fields.lot_nr")}>
                  {record.lot_nr}
                </Descriptions.Item>
              )}
              {record?.location && (
                <Descriptions.Item label={t("spool.fields.location")}>
                  {record.location}
                </Descriptions.Item>
              )}
              {record?.comment && (
                <Descriptions.Item label={t("spool.fields.comment")} span={2}>
                  {enrichText(record.comment)}
                </Descriptions.Item>
              )}
              <Descriptions.Item label={t("spool.fields.archived")}>
                {record?.archived ? t("yes") : t("no")}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        {/* Extra fields */}
        {extraFields?.data && extraFields.data.length > 0 && (
          <Col xs={24}>
            <Card title={t("settings.extra_fields.tab")} size="small">
              <Descriptions column={{ xs: 1, sm: 2 }} size="small" styles={{ label: { width: 140 } }}>
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

export default SpoolShow;
