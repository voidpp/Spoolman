import { Show } from "@refinedev/antd";
import { useShow, useTranslate } from "@refinedev/core";
import { Card, Col, Descriptions, Row, Space, Typography } from "antd";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { ExtraFieldDisplay } from "../../components/extraFields";
import { NumberFieldUnit } from "../../components/numberField";
import { enrichText } from "../../utils/parsing";
import { EntityType, useGetFields } from "../../utils/queryFields";
import { IVendor } from "./model";

dayjs.extend(utc);

const { Title, Text } = Typography;

const fmtDate = (val: string | undefined) => {
  if (!val) return "—";
  return dayjs.utc(val).local().format("YYYY-MM-DD HH:mm");
};

export const VendorShow = () => {
  const t = useTranslate();
  const extraFields = useGetFields(EntityType.vendor);

  const { query } = useShow<IVendor>({ liveMode: "auto" });
  const { data, isLoading } = query;
  const record = data?.data;

  const formatTitle = (item: IVendor) =>
    t("vendor.titles.show_title", { id: item.id, name: item.name, interpolation: { escapeValue: false } });

  return (
    <Show isLoading={isLoading} title={record ? formatTitle(record) : ""}>
      {/* ── Hero ── */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={32} align="middle" wrap>
          <Col flex="auto">
            <Space direction="vertical" size={4}>
              <Text type="secondary" style={{ fontSize: 12 }}>{t("vendor.fields.name")}</Text>
              <Title level={3} style={{ margin: 0 }}>{record?.name}</Title>
            </Space>
          </Col>
          <Col flex="none">
            <Text type="secondary" style={{ fontSize: 12 }}>{t("vendor.fields.registered")}</Text>
            <br />
            <Text>{fmtDate(record?.registered)}</Text>
          </Col>
        </Row>
      </Card>

      {/* ── Details grid ── */}
      <Row gutter={[16, 16]}>
        <Col xs={24}>
          <Card title={t("vendor.titles.details", "Details")} size="small">
            <Descriptions column={{ xs: 1, sm: 2 }} size="small" styles={{ label: { width: 160 } }}>
              <Descriptions.Item label={t("vendor.fields.id")}>#{record?.id}</Descriptions.Item>
              <Descriptions.Item label={t("vendor.fields.registered")}>{fmtDate(record?.registered)}</Descriptions.Item>
              {record?.empty_spool_weight != null && (
                <Descriptions.Item label={t("vendor.fields.empty_spool_weight")}>
                  <NumberFieldUnit value={record.empty_spool_weight} unit="g" options={{ maximumFractionDigits: 1 }} />
                </Descriptions.Item>
              )}
              {record?.external_id && (
                <Descriptions.Item label={t("vendor.fields.external_id")}>{record.external_id}</Descriptions.Item>
              )}
              {record?.comment && (
                <Descriptions.Item label={t("vendor.fields.comment")} span={2}>
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

export default VendorShow;
