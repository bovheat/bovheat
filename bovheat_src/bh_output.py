import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages


def write_xlsx(final_df, filename):
    filename += ".xlsx"

    writedf_dict = {"long": final_df, "wide": calc_long_to_wide(final_df)}

    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
        for name, df in writedf_dict.items():
            df.to_excel(writer, sheet_name=name, index=False)
            worksheet = writer.sheets[name]
            for i, width in enumerate(get_col_widths(df)):
                worksheet.set_column(i - 1, i - 1, width)

        writer.save()

    print(f"# XLSX: {filename} created.")


def calc_long_to_wide(final_df):
    wide_df = final_df.copy(deep=True)

    wide_df.set_index(
        [
            "foldername",
            "Cow Number",
            "lactation_adj",
            "calving_date",
            "act_usable",
            "act_max",
            "heat_count",
            "heat_no",
        ],
        inplace=True,
    )

    wide_df = wide_df.unstack("heat_no")
    wide_df = wide_df.sort_index(axis=1, level=1)

    #
    wide_df.drop(
        columns=[name_tuple for name_tuple in wide_df.columns if pd.isna(name_tuple[1])],
        inplace=True,
    )
    wide_df.columns = [f"{name}{heat_no}" for name, heat_no in wide_df.columns]
    wide_df.reset_index(inplace=True)

    return wide_df


def get_col_widths(dataframe):
    idx_max = max([len(str(s)) for s in dataframe.index.values] + [len(str(dataframe.index.name))])
    return [idx_max] + [
        max([len(str(s)) for s in dataframe[col].values] + [len(col)]) for col in dataframe.columns
    ]


def write_pdf(heats_df, sections_df, threshold, filename):

    filename += ".pdf"

    pdf_file = PdfPages(filename)  # Start PDF file

    # # example to paralalize group processing
    # def applyParallel(dfGrouped, func):
    #     with Pool(cpu_count()) as p:
    #         ret_list = p.map(func, [group for name, group in dfGrouped])
    #     return pandas.concat(ret_list)

    heats_df.groupby(["foldername", "Cow Number", "lactation_adj"]).apply(
        lambda df: build_pdf_page(
            cowdf=sections_df[
                (sections_df["foldername"].isin(df["foldername"]))
                & (sections_df["Cow Number"].isin(df["Cow Number"]))
                & (sections_df["lactation_adj"].isin(df["lactation_adj"]))
            ],
            heats_df=df,
            pdf_file=pdf_file,
            threshold=threshold,
        )
    )

    pdf_file.close()  # closing pdf

    print(f"\n# PDF: {filename} created.")


def build_pdf_page(cowdf, heats_df, pdf_file, threshold):
    print(
        "\r Building PDF for", cowdf["foldername"].iloc[0], cowdf["Cow Number"].iloc[0], end="",
    )

    cownumber = cowdf["Cow Number"].iloc[0]
    foldername = cowdf["foldername"].iloc[0]
    lactation_no = cowdf["lactation_adj"].iloc[0]

    plt.style.use("ggplot")
    _, ax = plt.subplots(figsize=(28, 12))

    cowdf.plot(
        ax=ax,
        kind="line",
        x="datetime",
        y="Activity Change",
        title=f"{foldername} : {cownumber:.0f}_L{lactation_no:.0f}  % "
        f"{heats_df['act_usable'].iloc[0]:.2f}",
    )

    ax.set_ylim([-50, 110])

    ax.axhline(threshold, label=f"{threshold}_thresh", color="black", linestyle=":")

    calving_date = cowdf["calving_date"].iloc[0]

    if cowdf["datetime"].isin([calving_date]).any():
        ax.axvline(
            calving_date + pd.Timedelta(hours=1), label="calving", color="black", linestyle="-",
        )

    for _, heat in heats_df[heats_df["heat_no"] > 0].groupby(["heat_no"]):
        ax.axvspan(
            heat["start_dt_heat"].iloc[0], heat["stop_dt_heat"].iloc[0], alpha=0.1, color="red",
        )

    plt.legend(loc="best")
    plt.savefig(pdf_file, bbox_inches="tight", format="pdf")

    plt.close()
