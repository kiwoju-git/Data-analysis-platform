import { useI18n } from "./i18n/LocaleProvider";
import { fullGroupName, type StoredGroupIdentity } from "./groupIdentity";
import "./groupIdentity.css";

export function GroupIdentityDetails({ groups }: { groups: readonly StoredGroupIdentity[] }) {
  const { t } = useI18n();
  return <>
    {groups.some((group) => group.group_value === undefined) ? <p className="notice-box" data-group-identity-legacy>{t("group_identity.legacy_labels")}</p> : null}
    <details className="technical-details group-identity-details" data-group-identities>
      <summary>{t("group_identity.full_names")}</summary>
      <table className="result-table"><tbody>
        {groups.map((group) => <tr key={group.group_index} data-group-index={group.group_index}>
          <th scope="row">{t("group_identity.group_number", { number: group.group_index + 1 })}</th>
          <td>{fullGroupName(group)}</td>
        </tr>)}
      </tbody></table>
    </details>
  </>;
}
