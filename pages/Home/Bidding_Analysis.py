
        # Keep From / To labels on the LEFT of the date boxes so the header uses
        # horizontal space instead of adding an extra label row above the inputs.
        with dates_col:
            from_lbl, from_box, to_lbl, to_box = st.columns(
                [0.30, 1.00, 0.20, 1.00],
                gap="small",
                vertical_alignment="center",
            )

            with from_lbl:
                st.markdown(
                    "<div class='bid-inline-date-label'>From</div>",
                    unsafe_allow_html=True,
                )

            with from_box:
                from_date = st.date_input(
                    "From",
                    value=st.session_state["bidding_from_date"],
                    format="DD/MM/YYYY",
                    key="bidding_from_date_input",
                    label_visibility="collapsed",
                )

            with to_lbl:
                st.markdown(
                    "<div class='bid-inline-date-label'>To</div>",
                    unsafe_allow_html=True,
                )

            with to_box:
                to_date = st.date_input(
                    "To",
                    value=st.session_state["bidding_to_date"],
                    format="DD/MM/YYYY",
                    key="bidding_to_date_input",
                    label_visibility="collapsed",
                )

        with run_col:
            load_clicked = st.button(
                "↻ Load / Refresh",
                type="primary",
                use_container_width=True,
                key="bidding_load_refresh",
            )

    if from_date > to_date:
        st.error("From Date cannot be greater than To Date.")
        return

    cached_raw = st.session_state.get("bidding_raw_data")
    needs_schema_refresh = (
        isinstance(cached_raw, pd.DataFrame)
        and not cached_raw.empty
        and "BIDDER_VENDOR_LIST" not in cached_raw.columns
    )

    should_load = (
        load_clicked
        or "bidding_raw_data" not in st.session_state
        or needs_schema_refresh
    )

    if should_load:
        st.session_state["bidding_from_date"] = from_date
        st.session_state["bidding_to_date"] = to_date

        try:
            with st.spinner("Loading bidding data..."):
                if load_clicked or needs_schema_refresh:
                    load_bidding_data.clear()

                raw_df = load_bidding_data(from_date, to_date)
                st.session_state["bidding_raw_data"] = raw_df

        except Exception as exc:
            st.error("Unable to load bidding data from SQL Server.")
            st.exception(exc)
            return

    raw_df = st.session_state.get("bidding_raw_data", pd.DataFrame())

    # Re-run lightweight derived calculations on cached data as well.
    # This ensures newly added control fields are available immediately
    # after a code deployment without forcing users to reload SQL first.
    if raw_df is not None and not raw_df.empty:
        raw_df = prepare_bidding_data(raw_df)
        st.session_state["bidding_raw_data"] = raw_df

    if raw_df is None or raw_df.empty:
        st.warning("No bidding data found for the selected date range.")
        return

    st.markdown(
        f"""
        <div class="bid-period-line">
            Loaded Period: {st.session_state['bidding_from_date'].strftime('%d/%m/%Y')}
            to {st.session_state['bidding_to_date'].strftime('%d/%m/%Y')}
            &nbsp;|&nbsp; {raw_df['BIDID'].nunique():,} unique bids
        </div>
        """,
        unsafe_allow_html=True,
    )

    filtered_df = apply_dashboard_filters(raw_df)

    if filtered_df.empty:
        st.warning("No records match the selected filters.")
        return

    render_kpis(filtered_df)
    render_charts(filtered_df)
    render_vehicle_type_insights(filtered_df)
    render_query_response_analysis(filtered_df)
    render_vendor_performance(filtered_df)
    render_exceptions(filtered_df)
    render_detail_table(filtered_df)

