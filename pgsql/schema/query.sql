drop table if exists query;

create table if not exists query (
	id serial primary key,
	xquery_id varchar(32) not null,
	xconnection_id varchar(32) not null,
	name varchar(32) not null,
	query_text text not null
);
